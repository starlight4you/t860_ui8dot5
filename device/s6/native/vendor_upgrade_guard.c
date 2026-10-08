/* Recovery-only read-only guard: the complete original S6 hardware tree.
 * Exactly one reviewed text policy may be in its original/adapted state.
 * All other contents, links, identities, labels and capabilities must match.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/xattr.h>
#include <unistd.h>
#include "sha256_readonly.h"
#include "vendor_upgrade_guard_table.h"

/* Static Bionic reserves its AArch64 TCB before executable TLS. Force the
 * required 64-byte PT_TLS alignment at link time, without binary rewriting.
 * https://android.googlesource.com/platform/bionic/+/140e4d35c/libc/bionic/bionic_elf_tls.cpp
 */
static __thread unsigned char recovery_tls_alignment
    __attribute__((aligned(64), used));

static int bad(const char *reason,const char *path) {
    fprintf(stderr,"t860-vendor-guard: %s: %s (errno=%d)\n",reason,path,errno);return -1;
}
static int find_item(const char *name) {
    size_t lo=0,hi=ITEM_COUNT;
    while(lo<hi){size_t mid=lo+(hi-lo)/2;int c=strcmp(name,items[mid].path);if(!c)return (int)mid;if(c<0)hi=mid;else lo=mid+1;}
    return -1;
}
static int open_item(int root,const char *name,int leaf_flags) {
    if(!strcmp(name,"."))return dup(root);
    char text[1024];if(strlen(name)>=sizeof(text)){errno=ENAMETOOLONG;return -1;}
    strcpy(text,name);char *part=text,*slash;int fd=dup(root);if(fd<0)return -1;
    while((slash=strchr(part,'/'))){*slash=0;int n=openat(fd,part,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);close(fd);if(n<0)return -1;fd=n;part=slash+1;}
    int n=openat(fd,part,leaf_flags|O_NOFOLLOW|O_CLOEXEC);close(fd);return n;
}
static int attributes(const char *path,const struct item *row) {
    ssize_t n=llistxattr(path,NULL,0);if(n<0||n>65536)return bad("xattr list unavailable",row->path);
    char *names=malloc((size_t)n+1);if(!names)return bad("allocation failure",row->path);
    if(llistxattr(path,names,(size_t)n)!=n){free(names);return bad("xattr list changed",row->path);}
    size_t off=0,count=0;
    while(off<(size_t)n){
        size_t len=strnlen(names+off,(size_t)n-off);if(len==(size_t)n-off){free(names);return bad("invalid xattr names",row->path);}
        const struct attr *wanted=NULL;
        for(size_t i=0;i<row->attr_count;i++)if(!strcmp(names+off,row->attrs[i].name)){wanted=&row->attrs[i];break;}
        if(!wanted){free(names);return bad("unexpected xattr",row->path);}
        ssize_t bytes=lgetxattr(path,names+off,NULL,0);size_t expected=strlen(wanted->hex)/2;
        int label=!strcmp(wanted->name,"security.selinux");
        /* SELinux-enabled Recovery exports a terminating NUL for the same
         * label even when ext4's original xattr omitted it. Only that label
         * terminator is canonicalized; capabilities and all other attrs are
         * byte-exact. Embedded NULs and every different label still fail.
         */
        if(bytes<0||bytes>65536||(!label&&(size_t)bytes!=expected)){free(names);return bad("xattr size mismatch",row->path);}
        unsigned char *v=malloc((size_t)bytes+1);if(!v){free(names);return bad("allocation failure",row->path);}
        if(lgetxattr(path,names+off,v,(size_t)bytes)!=bytes){free(v);free(names);return bad("xattr read mismatch",row->path);}
        size_t actual=(size_t)bytes;
        if(label){
            if(expected>=1&&!strcmp(wanted->hex+(expected-1)*2,"00"))expected--;
            if(actual>=1&&v[actual-1]==0)actual--;
            if(memchr(v,0,actual)){free(v);free(names);return bad("invalid label",row->path);}
        }
        if(actual!=expected){free(v);free(names);return bad("xattr size mismatch",row->path);}
        for(size_t i=0;i<expected;i++){
            char actual[3];snprintf(actual,sizeof(actual),"%02x",v[i]);
            if(memcmp(actual,wanted->hex+i*2,2)){free(v);free(names);return bad("xattr value mismatch",row->path);}
        }
        free(v);off+=len+1;count++;
    }
    free(names);if(count!=row->attr_count)return bad("missing xattr",row->path);return 0;
}
static int members(int fd,const char *parent,size_t *count,dev_t device) {
    DIR *d=fdopendir(dup(fd));if(!d)return bad("directory unavailable",parent);
    struct dirent *e;int result=0;errno=0;
    while((e=readdir(d))){
        if(!strcmp(e->d_name,".")||!strcmp(e->d_name,".."))continue;
        char name[1024];int size=snprintf(name,sizeof(name),!strcmp(parent,".")?"%s":"%s/%s",!strcmp(parent,".")?e->d_name:parent,e->d_name);
        if(size<0||size>=(int)sizeof(name)||find_item(name)<0){result=bad("unexpected vendor entry",name);break;}
        (*count)++;struct stat s;
        if(fstatat(fd,e->d_name,&s,AT_SYMLINK_NOFOLLOW)||s.st_dev!=device){result=bad("entry device mismatch",name);break;}
        if(S_ISDIR(s.st_mode)){
            int child=openat(fd,e->d_name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
            if(child<0){result=bad("directory open failure",name);break;}
            result=members(child,name,count,device);close(child);if(result)break;
        }
        errno=0;
    }
    if(!result&&errno)result=bad("directory read error",parent);closedir(d);return result;
}
int main(int argc,char **argv) {
    if(argc!=3||geteuid()!=0||(strcmp(argv[2],"any")&&strcmp(argv[2],"baseline")&&strcmp(argv[2],"adapted"))){fprintf(stderr,"usage: vendor-guard ABSOLUTE_VENDOR_MOUNT any|baseline|adapted (root only)\n");return 2;}
    if(argv[1][0]!='/'||strstr(argv[1],"/../")){return 2;}
    int root=open(argv[1],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(root<0){bad("root open",argv[1]);return 1;}
    struct stat initial;if(fstat(root,&initial)){close(root);return 1;}
    size_t count=1;int result=members(root,".",&count,initial.st_dev);int adapted=-1;
    if(count!=ITEM_COUNT&&!result)result=bad("vendor entry count mismatch",argv[1]);
    for(size_t i=0;i<ITEM_COUNT&&!result;i++){
        const struct item *row=&items[i];char path[2048];struct stat s;
        if(snprintf(path,sizeof(path),"%s/%s",argv[1],row->path)>=(int)sizeof(path)||fstatat(root,row->path,&s,AT_SYMLINK_NOFOLLOW)){result=bad("missing vendor entry",row->path);break;}
        if(s.st_dev!=initial.st_dev||s.st_mode!=row->mode||s.st_uid!=row->uid||s.st_gid!=row->gid||s.st_nlink!=row->nlink){result=bad("vendor metadata mismatch",row->path);break;}
        if(attributes(path,row)){result=-1;break;}
        if(S_ISLNK(s.st_mode)){
            char target[2048];ssize_t n=readlinkat(root,row->path,target,sizeof(target)-1);
            if(n<0||(size_t)n>=sizeof(target)-1){result=bad("symlink read failure",row->path);break;}
            target[n]=0;if(strcmp(target,row->link)){result=bad("symlink target mismatch",row->path);break;}
        } else if(S_ISREG(s.st_mode)){
            int fd=open_item(root,row->path,O_RDONLY);char digest[65];
            if(fd<0){result=bad("file open failure",row->path);break;}
            struct stat opened;
            if(fstat(fd,&opened)||opened.st_dev!=s.st_dev||opened.st_ino!=s.st_ino||hash_fd(fd,digest)){result=bad("file read identity mismatch",row->path);close(fd);break;}
            close(fd);
            if(!strcmp(row->path,POLICY_PATH)){
                if((uint64_t)s.st_size==row->bytes&&!strcmp(digest,row->sha))adapted=0;
                else if((uint64_t)s.st_size==POLICY_AFTER_BYTES&&!strcmp(digest,POLICY_AFTER_SHA))adapted=1;
                else {result=bad("unreviewed policy",row->path);break;}
            } else if((uint64_t)s.st_size!=row->bytes||strcmp(digest,row->sha)){result=bad("vendor content mismatch",row->path);break;}
            if(row->leader){
                struct stat leader;if(fstatat(root,row->leader,&leader,AT_SYMLINK_NOFOLLOW)||leader.st_dev!=s.st_dev||leader.st_ino!=s.st_ino){result=bad("hardlink topology mismatch",row->path);break;}
            }
        } else if(!S_ISDIR(s.st_mode)){result=bad("unsupported vendor entry type",row->path);break;}
    }
    close(root);
    if(result||adapted<0)return 1;
    if((!strcmp(argv[2],"baseline")&&adapted)||(!strcmp(argv[2],"adapted")&&!adapted)){bad("wrong policy state",POLICY_PATH);return 1;}
    puts(adapted?"ADAPTED":"BASELINE");return 0;
}
