/* A71 Recovery-only refusal check. No writes, signature bypass, or activation.
 * Factory versions come from the pinned candidate manifest table. Updated
 * files are NOT claimed verified: all active .apex files are refused. Names
 * and versions are diagnostic only; apexd selects by the content manifest.
 * Session state follows the original AOSP SessionState protobuf schema.
 */
#define _GNU_SOURCE
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static __thread unsigned char recovery_tls_alignment
    __attribute__((aligned(64), used));
struct module { char name[128]; uint64_t version; };
static struct module modules[128];
static size_t module_count, session_count;
static int fail(const char *why, const char *item) {
    fprintf(stderr, "t860-mainline-preflight: %s: %s\n", why, item);
    return -1;
}
static int component_ok(const char *s) {
    if (!*s || !strcmp(s, ".") || !strcmp(s, "..")) return 0;
    for (; *s; ++s) if (!(isalnum((unsigned char)*s) || *s == '_' || *s == '.')) return 0;
    return 1;
}
static int number(const char *s, uint64_t *v) {
    if (!*s) return -1;
    for (const char *p = s; *p; ++p) if (!isdigit((unsigned char)*p)) return -1;
    errno = 0; char *end = NULL;
    unsigned long long x = strtoull(s, &end, 10);
    if (errno || !end || *end || !x || x > INT64_MAX) return -1;
    *v = x; return 0;
}
/* Traverse every component without following symlinks. Paths are supplied by
 * the reviewed installer; absolute fixture paths use the same checks. */
static int open_directory(const char *path) {
    char text[PATH_MAX];
    if (path[0] != '/' || strlen(path) >= sizeof(text)) { errno = EINVAL; return -1; }
    strcpy(text, path + 1);
    int fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) return -1;
    char *part = text, *slash;
    while (*part) {
        slash = strchr(part, '/'); if (slash) *slash = 0;
        if (!*part || !strcmp(part, ".") || !strcmp(part, "..")) {
            close(fd); errno = EINVAL; return -1;
        }
        int next = openat(fd, part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        int saved = errno; close(fd); if (next < 0) { errno = saved; return -1; }
        fd = next; if (!slash) break; part = slash + 1;
    }
    return fd;
}
static int read_table(const char *path) {
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    struct stat st;
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_size <= 0 || st.st_size > 65536) {
        if (fd >= 0) close(fd); return fail("invalid factory table", path);
    }
    FILE *f = fdopen(fd, "r"); if (!f) { close(fd); return fail("table stream unavailable", path); }
    char line[256]; int result = 0;
    while (fgets(line, sizeof(line), f)) {
        size_t n = strlen(line); char *tab = strchr(line, '\t');
        if (!n || line[n-1] != '\n' || !tab || strchr(tab+1, '\t') || module_count >= 128) { result = -1; break; }
        line[n-1] = 0; *tab = 0;
        if (!component_ok(line) || strlen(line) >= sizeof(modules[0].name) ||
            number(tab+1, &modules[module_count].version)) { result = -1; break; }
        for (size_t i = 0; i < module_count; ++i) if (!strcmp(modules[i].name, line)) result = -1;
        if (result) break;
        strcpy(modules[module_count++].name, line);
    }
    if (ferror(f) || !module_count) result = -1;
    fclose(f); return result ? fail("malformed or duplicate factory identity", path) : 0;
}
static int active(const char *path) {
    int root = open_directory(path);
    if (root < 0) return errno == ENOENT ? 0 : fail("active directory unavailable/unsafe", path);
    DIR *d = fdopendir(root); if (!d) { close(root); return fail("active scan unavailable", path); }
    struct dirent *e; int result = 0; size_t entries = 0; errno = 0;
    while ((e = readdir(d))) {
        if (++entries > 10000) { result = fail("active entry limit", path); break; }
        size_t n = strlen(e->d_name);
        if (n < 5 || strcmp(e->d_name+n-5, ".apex")) { errno = 0; continue; }
        char name[256]; if (n >= sizeof(name)) { result = fail("invalid active name", e->d_name); break; }
        strcpy(name, e->d_name); name[n-5] = 0; char *at = strchr(name, '@');
        uint64_t version; struct stat st;
        if (!at || strchr(at+1, '@')) { result = fail("unversioned active APEX", e->d_name); break; }
        *at = 0;
        if (!component_ok(name) || number(at+1, &version) ||
            fstatat(dirfd(d), e->d_name, &st, AT_SYMLINK_NOFOLLOW) ||
            !S_ISREG(st.st_mode) || st.st_size <= 0) { result = fail("invalid active APEX", e->d_name); break; }
        /* A lower version in a filename does not prove the content is older.
         * Recovery cannot reliably read FBE-protected manifests; fail closed
         * until a content-based validation path is implemented and audited. */
        result = fail("active APEX content not verified; resolve updates before upgrade", e->d_name);
        break;
    }
    if (!result && errno) result = fail("active directory read failed", path);
    closedir(d); return result;
}
static int varint(const unsigned char *b, size_t n, size_t *at, uint64_t *out) {
    uint64_t v = 0;
    for (unsigned shift = 0; shift <= 63; shift += 7) {
        if (*at >= n) return -1;
        unsigned char x = b[(*at)++];
        if (shift == 63 && (x & 0xfe)) return -1;
        v |= (uint64_t)(x & 127) << shift;
        if (!(x & 128)) { *out = v; return 0; }
    }
    return -1;
}
static int state(int dir) {
    int fd = openat(dir, "state", O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    struct stat st;
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_size <= 0 || st.st_size > 1048576) {
        if (fd >= 0) close(fd); return -1;
    }
    size_t n = (size_t)st.st_size, got = 0;
    unsigned char *b = malloc(n); if (!b) { close(fd); return -1; }
    while (got < n) {
        ssize_t r = read(fd, b+got, n-got);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) { free(b); close(fd); return -1; }
        got += (size_t)r;
    }
    close(fd); size_t at = 0; int seen = 0, result = -1;
    while (at < n) {
        uint64_t tag, value;
        if (varint(b, n, &at, &tag) || !(tag >> 3) || (tag >> 3) > 0x1fffffff) goto done;
        unsigned wire = tag & 7;
        if (wire == 0) {
            if (varint(b, n, &at, &value)) goto done;
            if ((tag >> 3) == 2) {
                if (seen++ || value == 0 || value > 8) goto done;
                result = (int)value;
            }
        } else if (wire == 2 || wire == 1 || wire == 5) {
            if ((tag >> 3) == 2) goto done;
            if (wire == 2) { if (varint(b, n, &at, &value)) goto done; }
            else value = wire == 1 ? 8 : 4;
            if (value > n-at) goto done;
            at += (size_t)value;
        } else goto done;
    }
    if (seen == 1) { free(b); return result; }
done:
    free(b); return -1;
}
static int sessions(const char *path) {
    int root = open_directory(path);
    if (root < 0) return errno == ENOENT ? 0 : fail("session directory unavailable/unsafe", path);
    DIR *d = fdopendir(root); if (!d) { close(root); return fail("session scan unavailable", path); }
    struct dirent *e; int result = 0; size_t entries = 0; errno = 0;
    while ((e = readdir(d))) {
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) { errno = 0; continue; }
        uint64_t id;
        if (++entries > 10000 || number(e->d_name, &id) || id > INT32_MAX) { result = fail("invalid session name", e->d_name); break; }
        int fd = openat(dirfd(d), e->d_name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        if (fd < 0) { result = fail("session unavailable/unsafe", e->d_name); break; }
        int s = state(fd); close(fd);
        if (s < 0 || s == 2 || s == 6 || s == 8) {
            result = fail("staged, unresolved rollback, or unreadable session; resolve before upgrade", e->d_name); break;
        }
        session_count++; errno = 0;
    }
    if (!result && errno) result = fail("session directory read failed", path);
    closedir(d); return result;
}
int main(int argc, char **argv) {
    if (geteuid() != 0 || argc < 4 || argc > 10) {
        fprintf(stderr, "usage: mainline-guard FACTORY_TSV ACTIVE_DIR SESSION_DIR... (root, read only)\n"); return 2;
    }
    if (read_table(argv[1]) || active(argv[2])) return 1;
    for (int i = 3; i < argc; ++i) if (sessions(argv[i])) return 1;
    printf("PASS: %zu factory identities; no active APEX files; %zu non-staged sessions. No writes.\n",
           module_count, session_count);
    return 0;
}
