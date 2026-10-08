/* TWRP cp preserves file attrs here but omits directory security attrs.
 * Copy only source directory attrs to the unreferenced A82 pending tree.
 * Source/content/whole-tree digests are gated separately by the transaction.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <unistd.h>

static __thread unsigned char recovery_tls_alignment
    __attribute__((aligned(64), used));
static unsigned nodes, changed_dirs;
static int allowed(const char *n) {
    return !strcmp(n,"security.selinux") || !strcmp(n,"security.sehash");
}
static int attrs(int src,int dst,int apply,int directory) {
    char names[65536], targets[65536];
    ssize_t n=flistxattr(src,names,sizeof(names));
    ssize_t t=flistxattr(dst,targets,sizeof(targets));
    if (n<0 || t<0) return 20;
    for (ssize_t i=0;i<t;) {
        size_t len=strnlen(targets+i,(size_t)(t-i));
        if (!len || len>=(size_t)(t-i) || !allowed(targets+i)) return 21;
        int found=0;
        for (ssize_t j=0;j<n;) {
            size_t slen=strnlen(names+j,(size_t)(n-j));
            if (!slen || slen>=(size_t)(n-j)) return 22;
            if (!strcmp(targets+i,names+j)) found=1;
            j+=(ssize_t)slen+1;
        }
        if (!found) return 23; /* Never delete an unexpected target attr. */
        i+=(ssize_t)len+1;
    }
    int changed=0;
    for (ssize_t i=0;i<n;) {
        size_t len=strnlen(names+i,(size_t)(n-i));
        if (!len || len>=(size_t)(n-i) || !allowed(names+i)) return 24;
        unsigned char value[65536],actual[65536];
        ssize_t bytes=fgetxattr(src,names+i,value,sizeof(value));
        errno=0;
        ssize_t got=fgetxattr(dst,names+i,actual,sizeof(actual));
        if (bytes<0 || (got<0 && errno!=ENODATA)) return 25;
        if (bytes!=got || memcmp(value,actual,(size_t)bytes)) {
            if (!directory) return 26; /* File attrs must already match. */
            changed=1;
            if (apply && fsetxattr(dst,names+i,value,(size_t)bytes,0)) return 27;
        }
        i+=(ssize_t)len+1;
    }
    if (changed) changed_dirs++;
    return 0;
}
static int walk(int src,int dst,int apply,unsigned depth) {
    if (depth>32) return 10;
    struct stat a,b;
    if (fstat(src,&a) || fstat(dst,&b)) return 11;
    if ((!S_ISDIR(a.st_mode) && !S_ISREG(a.st_mode)) || a.st_mode!=b.st_mode ||
        a.st_uid!=b.st_uid || a.st_gid!=b.st_gid ||
        (S_ISREG(a.st_mode) && (a.st_size!=b.st_size || a.st_nlink!=1 || b.st_nlink!=1))) return 12;
    nodes++;
    int rc=attrs(src,dst,apply,S_ISDIR(a.st_mode));
    if (rc || !S_ISDIR(a.st_mode)) return rc;
    DIR *dir=fdopendir(dup(src));
    if (!dir) return 13;
    struct dirent *ent;
    errno=0;
    while ((ent=readdir(dir))) {
        if (!strcmp(ent->d_name,".") || !strcmp(ent->d_name,"..")) continue;
        int s=openat(src,ent->d_name,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
        int d=openat(dst,ent->d_name,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
        if (s<0 || d<0) rc=14;
        else rc=walk(s,d,apply,depth+1);
        if (s>=0) close(s);
        if (d>=0) close(d);
        if (rc) {closedir(dir);return rc;}
        errno=0;
    }
    rc=errno ? 15:0;
    closedir(dir);
    return rc;
}
int main(int argc,char **argv) {
    if (argc!=2 || geteuid()!=0 ||
        (strcmp(argv[1],"--check") && strcmp(argv[1],"--apply"))) return 2;
    int src=open("/cache/t860-metadata",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    int dst=open("/data/unencrypted/t860-metadata-a82-pending",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (src<0 || dst<0) return 3;
    int rc=walk(src,dst,!strcmp(argv[1],"--apply"),0);
    close(src);close(dst);
    if (rc) {fprintf(stderr,"Directory xattr transfer stopped, code %d\n",rc);return rc;}
    printf("A82_DIRECTORY_XATTRS_%s nodes=%u changed_dirs=%u\n",
           !strcmp(argv[1],"--apply") ? "APPLIED":"CHECKED",nodes,changed_dirs);
    return 0;
}
