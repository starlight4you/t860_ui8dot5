/* A75 failure recovery, reason: docs/MAINLINE_UPDATE_COMPAT_A75.md.
 * The audited check/bound implementation and table remain authoritative.
 * No unknown manifest is accepted and no BPF success is manufactured.
 */
#define main t860_guard_known_main
#include "tethering_guard.c"
#undef main
#include <time.h>

int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "timeout"))
        return t860_guard_known_main(argc, argv);
#ifdef GUARD_HOST_TEST
    /* Host has no Android property area. Do not pretend to test the timer. */
    return 64;
#else
    struct timespec start, now;
    if (clock_gettime(CLOCK_BOOTTIME, &start)) return 1;
    for (;;) {
        char state[PROP_VALUE_MAX];
        if (__system_property_get("bpf.t860.compat.bound", state) > 0 &&
            !strcmp(state, "true")) return 0;
        if (clock_gettime(CLOCK_BOOTTIME, &now)) return 1;
        if (now.tv_sec - start.tv_sec >= 900) {
            fail("900s without verified native binding; Recovery fallback",
                 "bpf.t860.compat.bound");
            return 1;
        }
        struct timespec pause = {.tv_sec = 1, .tv_nsec = 0};
        while (nanosleep(&pause, &pause) && errno == EINTR) {}
    }
#endif
}
