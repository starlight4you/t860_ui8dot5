/* Read-only inventory of exact reviewed metadata roots, including every xattr. */
#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <unistd.h>

static __thread unsigned char recovery_tls_alignment
    __attribute__((aligned(64), used));

static void hex(const void *text, size_t count) {
    const unsigned char *p = text;
    for (size_t i = 0; i < count; i++) printf("%02x", p[i]);
}

static int compare_names(const void *a, const void *b) {
    return strcmp(*(const char *const *)a, *(const char *const *)b);
}

static int walk(const char *root, const char *rel, unsigned depth) {
    if (depth > 32) return 10;
    char path[PATH_MAX];
    int n = snprintf(path, sizeof(path), "%s%s%s", root, *rel ? "/" : "", rel);
    if (n < 0 || n >= (int)sizeof(path)) return 11;
    struct stat st;
    if (lstat(path, &st)) return 12;
    if (!S_ISDIR(st.st_mode) && !S_ISREG(st.st_mode)) return 13;
    /* No hardlink flattening may be hidden by a cross-filesystem copy. */
    if (S_ISREG(st.st_mode) && st.st_nlink != 1) return 14;
    char names[65536];
    ssize_t count = llistxattr(path, names, sizeof(names));
    if (count < 0) return 15;
    hex(rel, strlen(rel));
    printf("\t%c\t%u\t%u\t%o\t%lld\t", S_ISDIR(st.st_mode) ? 'D' : 'F',
           st.st_uid, st.st_gid, st.st_mode,
           S_ISREG(st.st_mode) ? (long long)st.st_size : 0);
    char *ordered[256];
    size_t attribute_count = 0;
    for (ssize_t i = 0; i < count;) {
        size_t size = strnlen(names+i, (size_t)(count-i));
        if (!size || size >= (size_t)(count-i)) return 16;
        if (attribute_count == 256) return 21;
        ordered[attribute_count++] = names+i;
        i += (ssize_t)size+1;
    }
    qsort(ordered, attribute_count, sizeof(ordered[0]), compare_names);
    for (size_t i = 0; i < attribute_count; i++) {
        const char *name = ordered[i];
        size_t size = strlen(name);
        unsigned char value[65536];
        ssize_t bytes = lgetxattr(path, name, value, sizeof(value));
        if (bytes < 0) return 17;
        hex(name, size); putchar('='); hex(value, (size_t)bytes); putchar(';');
    }
    putchar('\n');
    if (S_ISDIR(st.st_mode)) {
        DIR *dir = opendir(path);
        if (!dir) return 18;
        struct dirent *entry;
        errno = 0;
        while ((entry = readdir(dir))) {
            if (!strcmp(entry->d_name,".") || !strcmp(entry->d_name,"..")) continue;
            char child[PATH_MAX];
            n = snprintf(child, sizeof(child), "%s%s%s", rel, *rel ? "/" : "", entry->d_name);
            if (n < 0 || n >= (int)sizeof(child)) { closedir(dir); return 19; }
            int result = walk(root, child, depth+1);
            if (result) { closedir(dir); return result; }
            errno = 0;
        }
        int error = errno;
        closedir(dir);
        if (error) return 20;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2 || geteuid() != 0 ||
        (strcmp(argv[1], "/cache/t860-metadata") &&
         strcmp(argv[1], "/cache/t860-metadata-a82-legacy-retained") &&
         strcmp(argv[1], "/data/unencrypted/t860-metadata") &&
         strcmp(argv[1], "/data/unencrypted/t860-metadata-a82-pending"))) return 2;
    int result = walk(argv[1], "", 0);
    if (result) fprintf(stderr, "Incomplete metadata inventory, code %d\n", result);
    return result;
}
