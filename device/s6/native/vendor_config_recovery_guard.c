/* Recovery-only repair eligibility, NOT a compatible vendor state.
 * Include the frozen full-tree read functions/table unchanged. Only the two
 * already-reviewed in-place text targets may have interrupted contents.
 * An independent restore must write pinned configs and rerun a strict guard.
 */
#define main frozen_strict_guard_main
#include "vendor_upgrade_guard.c"
#undef main

int main(int argc, char **argv) {
    if (argc != 3 || geteuid() != 0 || strcmp(argv[2], "recover-configs-only")) {
        fprintf(stderr, "usage: vendor-config-recovery-guard ABSOLUTE_VENDOR_MOUNT recover-configs-only (root only)\n");
        return 2;
    }
    if (argv[1][0] != '/' || strstr(argv[1], "/../")) return 2;
    int root = open(argv[1], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (root < 0) { bad("root open", argv[1]); return 1; }
    struct stat initial;
    if (fstat(root, &initial)) { close(root); return 1; }
    size_t count = 1, configs = 0;
    int result = members(root, ".", &count, initial.st_dev);
    if (!result && count != ITEM_COUNT) result = bad("vendor entry count mismatch", argv[1]);
    for (size_t i = 0; i < ITEM_COUNT && !result; i++) {
        const struct item *row = &items[i];
        char path[2048]; struct stat s;
        if (snprintf(path, sizeof(path), "%s/%s", argv[1], row->path) >= (int)sizeof(path)
                || fstatat(root, row->path, &s, AT_SYMLINK_NOFOLLOW)) {
            result = bad("missing vendor entry", row->path); break;
        }
        if (s.st_dev != initial.st_dev || s.st_mode != row->mode || s.st_uid != row->uid
                || s.st_gid != row->gid || s.st_nlink != row->nlink) {
            result = bad("vendor metadata mismatch", row->path); break;
        }
        if (attributes(path, row)) { result = -1; break; }
        if (S_ISLNK(s.st_mode)) {
            char target[2048]; ssize_t n = readlinkat(root, row->path, target, sizeof(target) - 1);
            if (n < 0 || (size_t)n >= sizeof(target) - 1) { result = bad("symlink read failure", row->path); break; }
            target[n] = 0;
            if (strcmp(target, row->link)) { result = bad("symlink target mismatch", row->path); break; }
        } else if (S_ISREG(s.st_mode)) {
            int fd = open_item(root, row->path, O_RDONLY); char digest[65]; struct stat opened;
            if (fd < 0) { result = bad("file open failure", row->path); break; }
            if (fstat(fd, &opened) || opened.st_dev != s.st_dev || opened.st_ino != s.st_ino || hash_fd(fd, digest)) {
                result = bad("file read identity mismatch", row->path); close(fd); break;
            }
            close(fd);
            uint64_t maximum = 0;
            if (!strcmp(row->path, "etc/vintf/compatibility_matrix.xml")) maximum = 3435;
            if (!strcmp(row->path, POLICY_PATH)) maximum = POLICY_AFTER_BYTES;
            if (maximum) {
                if (s.st_size < 0 || (uint64_t)s.st_size > maximum || row->nlink != 1 || row->leader) {
                    result = bad("config repair scope mismatch", row->path); break;
                }
                configs++;
            } else if ((uint64_t)s.st_size != row->bytes || strcmp(digest, row->sha)) {
                result = bad("vendor content mismatch", row->path); break;
            }
            if (row->leader) {
                struct stat leader;
                if (fstatat(root, row->leader, &leader, AT_SYMLINK_NOFOLLOW)
                        || leader.st_dev != s.st_dev || leader.st_ino != s.st_ino) {
                    result = bad("hardlink topology mismatch", row->path); break;
                }
            }
        } else if (!S_ISDIR(s.st_mode)) {
            result = bad("unsupported vendor entry type", row->path); break;
        }
    }
    close(root);
    if (result || configs != 2) return 1;
    puts("CONFIGS_RECOVERABLE");
    return 0;
}
