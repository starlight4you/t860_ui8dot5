/* Read-only proof of non-CE backing. No key, policy or inode changes. */
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <linux/fscrypt.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

static __thread unsigned char recovery_tls_alignment
    __attribute__((aligned(64), used));

int main(int argc, char **argv) {
    if (argc != 2 || geteuid() != 0 ||
        (strcmp(argv[1], "/data") && strcmp(argv[1], "/data/unencrypted") &&
         strcmp(argv[1], "/data/unencrypted/t860-metadata") &&
         strcmp(argv[1], "/data/unencrypted/t860-metadata-a82-pending"))) return 2;
    int fd = open(argv[1], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) { perror("open reviewed directory"); return 3; }
    struct stat st;
    long flags = 0;
    if (fstat(fd, &st) || ioctl(fd, FS_IOC_GETFLAGS, &flags)) {
        perror("stat/GETFLAGS"); close(fd); return 4;
    }
    struct fscrypt_policy_v1 policy;
    memset(&policy, 0, sizeof(policy));
    errno = 0;
    int rc = ioctl(fd, FS_IOC_GET_ENCRYPTION_POLICY, &policy);
    int error = errno;
    printf("path=%s uid=%u gid=%u mode=%o inode_flags=%lx policy_rc=%d policy_errno=%d\n",
           argv[1], st.st_uid, st.st_gid, st.st_mode & 07777, flags, rc, error);
    close(fd);
    /* Missing policy, not an unsupported or inaccessible policy query. */
    return (!(flags & FS_ENCRYPT_FL) && rc == -1 && error == ENODATA) ? 0 : 5;
}
