/* Ephemeral BPF ABI probe: no pins, no programs, closes every map FD. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <unistd.h>

int main(void) {
    struct utsname u;
    if (uname(&u)) return 1;
    printf("kernel=%s uid=%u\n", u.release, (unsigned)getuid());
    for (unsigned named = 0; named < 2; named++) {
        uint32_t attr[38] = {0};
        attr[0] = 1; /* BPF_MAP_TYPE_HASH */
        attr[1] = 4;
        attr[2] = 2;
        attr[3] = 16; /* Same ABI as donor tos_policy_mobile_map. */
        if (named) memcpy((char *)attr + 28, "tos_policy_mobi", 15);
        errno = 0;
        long fd = syscall(__NR_bpf, 0, attr, sizeof(attr));
        int error = errno;
        printf("map_name=%s attr_bytes=%zu fd=%ld errno=%d (%s)\n",
               named ? "tos_policy_mobi" : "<zero>", sizeof(attr), fd, error, strerror(error));
        if (fd >= 0) close((int)fd);
    }
    return 0;
}
