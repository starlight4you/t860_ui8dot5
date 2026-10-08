/* Read-only full SYSTEM uid/gid/mode/nlink/size/symlink/every-xattr inventory.
 * Timestamps intentionally excluded because read/write verification changes them.
 */
#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <unistd.h>
static __thread unsigned char recovery_tls_alignment __attribute__((aligned(64),used));
static void hex(const void *p0,size_t n) { const unsigned char *p=p0; for(size_t i=0;i<n;i++)printf("%02x",p[i]); }
static int cmpnames(const void *a,const void *b){return strcmp(*(const char *const *)a,*(const char *const *)b);}
static int walk(const char *root,const char *rel,unsigned depth,dev_t dev){
 if(depth>64)return 10;
 char path[PATH_MAX];int n=snprintf(path,sizeof(path),"%s%s%s",root,*rel?"/":"",rel);
 if(n<0||n>=(int)sizeof(path))return 11;
 struct stat st;if(lstat(path,&st)||st.st_dev!=dev)return 12;
 char type=S_ISDIR(st.st_mode)?'D':S_ISREG(st.st_mode)?'F':S_ISLNK(st.st_mode)?'L':'?';
 if(type=='?')return 13;
 char names[65536];ssize_t count=llistxattr(path,names,sizeof(names));if(count<0)return 15;
 hex(rel,strlen(rel));printf("\t%c\t%u\t%u\t%o\t%lu\t%lld\t",type,st.st_uid,st.st_gid,st.st_mode,
  (unsigned long)st.st_nlink,type=='D'?0:(long long)st.st_size);
 char *ordered[256];size_t ac=0;
 for(ssize_t i=0;i<count;){size_t size=strnlen(names+i,(size_t)(count-i));
  if(!size||size>=(size_t)(count-i)||ac==256)return 16;
  ordered[ac++]=names+i;i+=(ssize_t)size+1;}
 qsort(ordered,ac,sizeof(ordered[0]),cmpnames);
 for(size_t i=0;i<ac;i++){unsigned char value[65536];ssize_t size=lgetxattr(path,ordered[i],value,sizeof(value));
  if(size<0)return 17;hex(ordered[i],strlen(ordered[i]));putchar('=');hex(value,(size_t)size);putchar(';');}
 putchar('\t');if(type=='L'){char link[PATH_MAX];ssize_t size=readlink(path,link,sizeof(link));if(size<0||size==(ssize_t)sizeof(link))return 18;hex(link,(size_t)size);}
 putchar('\n');if(type!='D')return 0;
 DIR *d=opendir(path);if(!d)return 19;struct dirent *e;errno=0;
 while((e=readdir(d))){if(!strcmp(e->d_name,".")||!strcmp(e->d_name,".."))continue;
  char child[PATH_MAX];n=snprintf(child,sizeof(child),"%s%s%s",rel,*rel?"/":"",e->d_name);
  if(n<0||n>=(int)sizeof(child)){closedir(d);return 20;}
  int r=walk(root,child,depth+1,dev);if(r){closedir(d);return r;}errno=0;}
 int err=errno;closedir(d);return err?21:0;
}
int main(int argc,char **argv){
 if(argc!=2||geteuid()!=0||strncmp(argv[1],"/tmp/t860-A95-",14)||strstr(argv[1],".."))return 2;
 size_t n=strlen(argv[1]);if(n<7||strcmp(argv[1]+n-7,"/system"))return 3;
 struct stat st;if(lstat(argv[1],&st)||!S_ISDIR(st.st_mode))return 4;
 int r=walk(argv[1],"",0,st.st_dev);if(r)fprintf(stderr,"Incomplete SYSTEM inventory %d\n",r);return r;
}
