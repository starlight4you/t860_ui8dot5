/* Read-only directory access diagnosis; never treats EACCES as empty DATA.
 * Reuse the frozen component-by-component O_NOFOLLOW path traversal.
 * No encrypted file contents, account data, keys, or directory names emitted.
 */
#define main frozen_mainline_guard_main
#include "mainline_upgrade_guard.c"
#undef main
#include <sys/ioctl.h>
#include <linux/fs.h>

int main(int argc, char **argv) {
    if (geteuid() != 0 || argc < 2 || argc > 20) return 2;
    int failed = 0;
    for (int i = 1; i < argc; i++) {
        int fd = open_directory(argv[i]);
        if (fd < 0) {
            int saved = errno;
            printf("%s path=%s errno=%d reason=%s\n",
                   saved == ENOENT ? "ABSENT" : "UNAVAILABLE",
                   argv[i], saved, strerror(saved));
            if (saved != ENOENT) failed = 1;
            continue;
        }
        int flags = 0;
        int flags_ok = ioctl(fd, FS_IOC_GETFLAGS, &flags) == 0;
        int flags_errno = flags_ok ? 0 : errno;
        DIR *dir = fdopendir(fd);
        if (!dir) {
            int saved = errno; close(fd); failed = 1;
            printf("UNAVAILABLE path=%s errno=%d reason=%s\n", argv[i], saved, strerror(saved));
            continue;
        }
        size_t count = 0; struct dirent *entry;
        errno = 0;
        while ((entry = readdir(dir))) {
            if (strcmp(entry->d_name, ".") && strcmp(entry->d_name, "..")) count++;
            if (count > 10000) { errno = EOVERFLOW; break; }
            errno = 0;
        }
        int saved = errno; closedir(dir);
        if (saved) {
            failed = 1;
            printf("UNAVAILABLE path=%s errno=%d reason=%s\n", argv[i], saved, strerror(saved));
        } else {
            printf("READABLE path=%s entries=%zu encrypted=%s flags_errno=%d\n",
                   argv[i], count, flags_ok ? ((flags & FS_ENCRYPT_FL) ? "yes" : "no") : "unknown", flags_errno);
        }
    }
    return failed ? 1 : 0;
}
