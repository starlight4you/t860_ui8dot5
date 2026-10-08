/* A99 does not validate opaque active APEX contents. This mode may only be
 * used by the installer when source SYSTEM equals the exact target raw image,
 * PRODUCT has no factory APEX changes, and no pending session/checkpoint exists.
 * It preserves already-active modules during an identical-system reinstall.
 * First installation uses the original strict active-content refusal instead.
 */
#define main a71_guard_main
#include "mainline_upgrade_guard.c"
#undef main

struct retained_apex { const char *name; off_t size; };
static const struct retained_apex retained[] = {
    {"com.android.adservices@372038020.apex", 22716416},
    {"com.android.ondevicepersonalization@372038020.apex", 14999552},
    {"com.android.os.statsd@372040000.apex", 3825664},
    {"com.android.tzdata@372038420.apex", 929792},
};

static int backup_entry(int fd, const char *name);
static int retained_entries(const char *path) {
    int fd = open_directory(path);
    if (fd < 0) return errno == ENOENT ? 0 : fail("unsafe active root", path);
    DIR *d = fdopendir(fd);
    if (!d) { close(fd); return -1; }
    struct dirent *e; unsigned seen = 0; int result = 0; errno = 0;
    while ((e = readdir(d))) {
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) { errno = 0; continue; }
        if (strstr(e->d_name, ".apex.A")) {
            if (backup_entry(dirfd(d), e->d_name)) { result=-1;break; }
            errno=0;continue;
        }
        size_t i;
        for (i = 0; i < sizeof(retained)/sizeof(retained[0]); ++i)
            if (!strcmp(e->d_name, retained[i].name)) break;
        struct stat st;
        if (i == sizeof(retained)/sizeof(retained[0]) || (seen & (1u << i)) ||
            fstatat(dirfd(d), e->d_name, &st, AT_SYMLINK_NOFOLLOW) ||
            !S_ISREG(st.st_mode) || st.st_uid != 1000 || st.st_gid != 1000 ||
            (st.st_mode & 07777) != 0644 || st.st_size != retained[i].size) {
            result = fail("unreviewed active entry; preserve-mode refused", e->d_name); break;
        }
        seen |= 1u << i; errno = 0;
    }
    if (!result && errno) result = -1;
    closedir(d);
    /* Empty factory state or all four observed entries; no partial activation. */
    if (!result && seen && seen != 15) return fail("partial retained active set", path);
    return result;
}


/* UI8 upgrade: preserve encrypted module inodes under ignored backup suffixes.
 * No authentication/CE data is opened and no APEX content is claimed verified.
 */
#include <sys/syscall.h>
struct upgrade_entry { char name[256]; struct stat original; };
static struct upgrade_entry upgrades[128];
static size_t upgrade_count;
static int backup_entry(int fd,const char *name) {
    char text[256];if(strlen(name)>=sizeof(text))return -1;
    strcpy(text,name);char *suffix=strstr(text,".apex.A");if(!suffix)return -1;
    char *h=suffix+7,*digits=h;while(isdigit((unsigned char)*h))h++;
    if(h==digits || strcmp(h,"-held"))return -1;
    *suffix=0;char *at=strchr(text,'@');uint64_t version;
    if(!at || strchr(at+1,'@'))return -1;*at=0;
    if(number(at+1,&version))return -1;
    size_t i;for(i=0;i<module_count;i++)if(!strcmp(text,modules[i].name))break;
    struct stat st;
    return i==module_count || fstatat(fd,name,&st,AT_SYMLINK_NOFOLLOW) ||
        !S_ISREG(st.st_mode) || st.st_uid!=1000 || st.st_gid!=1000 ||
        (st.st_mode&07777)!=0644 || st.st_size<=0 || st.st_size>1073741824 ? -1:0;
}
static int upgrade_scan(const char *path) {
    int fd=open_directory(path);
    if (fd<0) return errno==ENOENT ? 0:fail("unsafe upgrade active root",path);
    DIR *d=fdopendir(fd); if(!d){close(fd);return -1;}
    struct dirent *e;int result=0;errno=0;
    while((e=readdir(d))) {
        if(!strcmp(e->d_name,".") || !strcmp(e->d_name,"..")){errno=0;continue;}
        size_t len=strlen(e->d_name);char text[256];
        if(len>=sizeof(text)){result=-1;break;}
        strcpy(text,e->d_name);char *suffix=strstr(text,".apex");
        int held=0;
        if(!suffix){result=fail("unexpected active entry",e->d_name);break;}
        if(suffix[5]) {
            char *h=suffix+5;
            if(strncmp(h,".A",2)){result=-1;break;}
            h+=2;char *digits=h;while(isdigit((unsigned char)*h))h++;
            if(h==digits || strcmp(h,"-held")){result=-1;break;}
            held=1;
        }
        *suffix=0;char *at=strchr(text,'@');uint64_t version;
        if(!at || strchr(at+1,'@')){result=-1;break;}
        *at=0;
        size_t i;for(i=0;i<module_count;i++)if(!strcmp(text,modules[i].name))break;
        struct stat st;
        if(i==module_count || number(at+1,&version) ||
           fstatat(fd,e->d_name,&st,AT_SYMLINK_NOFOLLOW) || !S_ISREG(st.st_mode) ||
           st.st_uid!=1000 || st.st_gid!=1000 || (st.st_mode&07777)!=0644 ||
           st.st_size<=0 || st.st_size>1073741824) {
            result=fail("unreviewed upgrade active entry",e->d_name);break;
        }
        if(!held) {
            if(upgrade_count>=128){result=-1;break;}
            char target[288];snprintf(target,sizeof(target),"%s.A99-held",e->d_name);
            struct stat exists;
            if(fstatat(fd,target,&exists,AT_SYMLINK_NOFOLLOW)==0 || errno!=ENOENT) {
                result=fail("backup collision",target);break;
            }
            strcpy(upgrades[upgrade_count].name,e->d_name);
            upgrades[upgrade_count++].original=st;
        }
        errno=0;
    }
    if(!result && errno)result=-1;
    closedir(d);return result;
}
static int upgrade_hold(const char *path) {
    if(!upgrade_count)return 0;
    int fd=open_directory(path);if(fd<0)return -1;
    size_t changed=0;int result=0;
    for(size_t i=0;i<upgrade_count;i++) {
        struct stat now;struct stat *old=&upgrades[i].original;
        if(fstatat(fd,upgrades[i].name,&now,AT_SYMLINK_NOFOLLOW) ||
           now.st_ino!=old->st_ino || now.st_dev!=old->st_dev || now.st_size!=old->st_size ||
           now.st_mode!=old->st_mode || now.st_uid!=old->st_uid || now.st_gid!=old->st_gid) {result=-1;break;}
        char target[288];snprintf(target,sizeof(target),"%s.A99-held",upgrades[i].name);
        if(syscall(SYS_renameat2,fd,upgrades[i].name,fd,target,1)) {result=-1;break;}
        changed++;
        if(fstatat(fd,target,&now,AT_SYMLINK_NOFOLLOW) || now.st_ino!=old->st_ino ||
           now.st_dev!=old->st_dev || now.st_size!=old->st_size || now.st_mode!=old->st_mode ||
           now.st_uid!=old->st_uid || now.st_gid!=old->st_gid){result=-1;break;}
    }
    if(result) {
        while(changed) {
            size_t i=--changed;char target[288];snprintf(target,sizeof(target),"%s.A99-held",upgrades[i].name);
            if(syscall(SYS_renameat2,fd,target,fd,upgrades[i].name,1))
                fprintf(stderr,"Backup retained; restore required: %s\n",target);
        }
    }
    if(fsync(fd))result=-1;close(fd);
    if(!result)printf("Preserved %zu old active module inodes with .A99-held suffix; no module content or user data deleted.\n",upgrade_count);
    return result;
}
int main(int argc, char **argv) {
    if(argc>=2 && (!strcmp(argv[1],"--upgrade-preflight") || !strcmp(argv[1],"--upgrade-hold"))) {
        if(geteuid() || argc<5 || argc>14)return 2;
        if(read_table(argv[2]) || upgrade_scan(argv[3]))return 1;
        for(int i=4;i<argc;i++)if(sessions(argv[i]))return 1;
        if(!strcmp(argv[1],"--upgrade-hold"))return upgrade_hold(argv[3]) ? 1:0;
        printf("PASS: %zu old active entries eligible for inode-preserving backup; no content validation or writes.\n",upgrade_count);
        return 0;
    }

    if (argc < 2 || strcmp(argv[1], "--identical-system-reinstall"))
        return a71_guard_main(argc, argv);
    if (geteuid() || argc < 5 || argc > 14) return 2;
    if (read_table(argv[2]) || retained_entries(argv[3])) return 1;
    for (int i = 4; i < argc; ++i) if (sessions(argv[i])) return 1;
    printf("PASS: identical-SYSTEM reinstall session checks; active contents preserved, not read/verified; %zu sessions. No writes.\n", session_count);
    return 0;
}
