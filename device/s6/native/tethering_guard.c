/* Read-only identity and metadata guard for the reviewed donor native views.
 * The production build has no alternate root or testing property backend.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/xattr.h>
#include <unistd.h>
#ifndef GUARD_HOST_TEST
#include <sys/system_properties.h>
#endif
#include "tethering_guard_table.h"

struct digest { uint32_t s[8]; uint64_t bytes; size_t used; unsigned char block[64]; };
static uint32_t rotr(uint32_t v, unsigned n) { return (v >> n) | (v << (32 - n)); }
static void transform(struct digest *d, const unsigned char *p) {
    static const uint32_t k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint32_t w[64];
    for (size_t i=0; i<16; i++) w[i]=((uint32_t)p[i*4]<<24)|((uint32_t)p[i*4+1]<<16)|((uint32_t)p[i*4+2]<<8)|p[i*4+3];
    for (size_t i=16; i<64; i++) w[i]=w[i-16]+(rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10));
    uint32_t a=d->s[0],b=d->s[1],c=d->s[2],e=d->s[4],f=d->s[5],g=d->s[6],h=d->s[7],v=d->s[3];
    for (size_t i=0; i<64; i++) {
        uint32_t t=h+(rotr(e,6)^rotr(e,11)^rotr(e,25))+((e&f)^((~e)&g))+k[i]+w[i];
        uint32_t u=(rotr(a,2)^rotr(a,13)^rotr(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=v+t;v=c;c=b;b=a;a=t+u;
    }
    d->s[0]+=a;d->s[1]+=b;d->s[2]+=c;d->s[3]+=v;d->s[4]+=e;d->s[5]+=f;d->s[6]+=g;d->s[7]+=h;
}
static void update(struct digest *d, const unsigned char *p, size_t n) {
    d->bytes+=n;
    while (n) {
        size_t z=64-d->used;if(z>n)z=n;
        memcpy(d->block+d->used,p,z);d->used+=z;p+=z;n-=z;
        if(d->used==64){transform(d,d->block);d->used=0;}
    }
}
static int hash_fd(int fd, char hex[65]) {
    struct digest d={{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19},0,0,{0}};
    unsigned char buf[32768];ssize_t n;
    while((n=read(fd,buf,sizeof(buf)))!=0){if(n<0){if(errno==EINTR)continue;return -1;}update(&d,buf,(size_t)n);}
    uint64_t bits=d.bytes*8;
    unsigned char end[128]={0x80};size_t z=d.used<56?56-d.used:120-d.used;
    for(size_t i=0;i<8;i++)end[z+i]=(unsigned char)(bits>>(56-i*8));
    update(&d,end,z+8);
    for(size_t i=0;i<8;i++)snprintf(hex+i*8,9,"%08x",d.s[i]);
    return 0;
}
static int log_fd(void) {
    /* init publishes the inherited file descriptor; its number is not fixed. */
    const char *value=getenv("ANDROID_FILE__dev_kmsg");char *end;long fd;
    if(!value||!*value)return -1;
    errno=0;fd=strtol(value,&end,10);
    if(errno||*end||fd<3||fd>INT_MAX)return -1;
    return (int)fd;
}
static int fail(const char *why, const char *path) {
    int error=errno;
    fprintf(stderr,"t860-tethering-guard: %s: %s (errno=%d)\n",why,path,error);
    int fd=log_fd();
    if(fd>=0)dprintf(fd,"<3>t860-tethering-guard: %s: %s (errno=%d)\n",why,path,error);
    return -1;
}
static int open_relative(int root, const char *name, int leaf_flags) {
    char text[256];if(strlen(name)>=sizeof(text)){errno=ENAMETOOLONG;return -1;}
    strcpy(text,name);char *part=text,*slash;int fd=dup(root);if(fd<0)return -1;
    while((slash=strchr(part,'/'))){*slash=0;int next=openat(fd,part,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);close(fd);if(next<0)return -1;fd=next;part=slash+1;}
    int result=openat(fd,part,leaf_flags|O_NOFOLLOW|O_CLOEXEC);close(fd);return result;
}
static int metadata(int fd, const struct item *i, int directory) {
    struct stat s;char label[128];ssize_t n;
    if(fstat(fd,&s)|| (directory?!S_ISDIR(s.st_mode):!S_ISREG(s.st_mode)) ||
       s.st_uid!=i->uid || s.st_gid!=i->gid || (s.st_mode&07777)!=i->mode ||
       (!directory && (uint64_t)s.st_size!=i->bytes))return fail("metadata mismatch",i->path);
    n=fgetxattr(fd,"security.selinux",label,sizeof(label));if(n<0)return fail("label read failed",i->path);
    while(n>0&&label[n-1]==0)n--;
    if((size_t)n!=strlen(i->label)||memcmp(label,i->label,(size_t)n))return fail("label mismatch",i->path);
    return 0;
}
static int known(const char *name, int *directory) {
    for(size_t i=0;i<FILE_COUNT;i++)if(!strcmp(name,files[i].path)){*directory=0;return 1;}
    for(size_t i=0;i<DIR_COUNT;i++)if(!strcmp(name,dirs[i].path)){*directory=1;return 1;}
    return 0;
}
static int members(int root, const char *relative) {
    int fd=open_relative(root,relative,O_RDONLY|O_DIRECTORY);if(fd<0)return fail("directory open failed",relative);
    DIR *d=fdopendir(fd);if(!d){close(fd);return fail("directory read failed",relative);}
    struct dirent *e;errno=0;int result=0;
    while((e=readdir(d))){
        if(!strcmp(e->d_name,".")||!strcmp(e->d_name,".."))continue;
        char path[256];int directory;
        if(snprintf(path,sizeof(path),"%s/%s",relative,e->d_name)>=(int)sizeof(path)||!known(path,&directory)){result=fail("unexpected native entry",relative);break;}
        if(directory&&members(root,path)){result=-1;break;}
        errno=0;
    }
    if(!result&&errno)result=fail("directory iteration failed",relative);
    closedir(d);return result;
}
static int view(int root, int patched) {
    for(size_t i=0;i<DIR_COUNT;i++){
        int fd=open_relative(root,dirs[i].path,O_RDONLY|O_DIRECTORY);if(fd<0)return fail("missing native directory",dirs[i].path);
        int r=metadata(fd,&dirs[i],1);close(fd);if(r)return r;
    }
    if(members(root,"bin")||members(root,"lib64"))return -1;
    for(size_t i=0;i<FILE_COUNT;i++){
        int fd=open_relative(root,files[i].path,O_RDONLY);if(fd<0)return fail("native file open failed",files[i].path);
        char hash[65];int r=metadata(fd,&files[i],0);
        if(!r&&(hash_fd(fd,hash)||strcmp(hash,patched?files[i].after:files[i].before)))r=fail("native SHA mismatch",files[i].path);
        close(fd);if(r)return r;
    }
    return 0;
}
static int root_dir(const char *name, int allow_alias) {
#ifdef GUARD_HOST_TEST
    char path[1024];const char *prefix=getenv("T860_GUARD_TEST_ROOT");
    if(!prefix||snprintf(path,sizeof(path),"%s%s",prefix,name)>=(int)sizeof(path)){errno=EINVAL;return -1;}
    name=path;
#endif
    return open(name,O_RDONLY|O_DIRECTORY|O_CLOEXEC|(allow_alias?0:O_NOFOLLOW));
}
int main(int argc, char **argv) {
#ifdef GUARD_HOST_TEST
    if(argc==3&&!strcmp(argv[1],"hash")){
        int fd=open(argv[2],O_RDONLY|O_NOFOLLOW);char h[65];if(fd<0||hash_fd(fd,h))return 1;close(fd);puts(h);return 0;
    }
#endif
    if(argc!=2||(strcmp(argv[1],"check")&&strcmp(argv[1],"bound")))return 64;
    int bound=!strcmp(argv[1],"bound");
#ifndef GUARD_HOST_TEST
    char sdk[PROP_VALUE_MAX];
    if(__system_property_get("ro.build.version.sdk",sdk)<=0||strcmp(sdk,"36"))return fail("unexpected platform SDK","ro.build.version.sdk")?1:0;
#endif
    int apex=root_dir("/apex/com.android.tethering",1),source=root_dir("/system/etc/t860-tethering-native",0);
    if(apex<0||source<0){fail("native root unavailable","APEX/source");return 1;}
    int fd=open_relative(apex,"apex_manifest.pb",O_RDONLY);struct stat s;char hash[65];
    if(fd<0||fstat(fd,&s)||!S_ISREG(s.st_mode)||s.st_size!=MANIFEST_BYTES||hash_fd(fd,hash)||strcmp(hash,MANIFEST_SHA)){
        fail("unreviewed active APEX manifest","apex_manifest.pb");if(fd>=0)close(fd);close(apex);close(source);return 1;
    }
    close(fd);int result=view(source,1)||view(apex,bound);close(source);close(apex);if(result)return 1;
    const char *key=bound?"bpf.t860.compat.bound":"bpf.t860.compat.checked";
#ifdef GUARD_HOST_TEST
    printf("HOST_TEST_PROPERTY %s=true\n",key);
#else
    if(__system_property_set(key,"true")){fail("property set failed",key);return 1;}
#endif
    fprintf(stderr,"t860-tethering-guard: %s verified; real BPF load status unchanged\n",argv[1]);
    int log=log_fd();if(log>=0)dprintf(log,"<6>t860-tethering-guard: %s verified\n",argv[1]);return 0;
}
