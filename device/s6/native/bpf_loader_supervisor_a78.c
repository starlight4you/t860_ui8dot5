/* Reason before modification: docs/MAINLINE_NATIVE_REBASE_A78.md.
 * Preserve the real loader's success/failure; allow apexd to revert on failure.
 * Does not publish any BPF property or create/attach/pin a BPF object itself.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifdef SUPERVISOR_HOST_TEST
/* Only the host binary has an alternate child and shortened time window. */
#define DEADLINE_SECONDS 3
#else
#define DEADLINE_SECONDS 900
#endif

static void log_event(const char *event, int status) {
    fprintf(stderr, "t860-bpf-supervisor: %s (status=%d)\n", event, status);
    const char *value = getenv("ANDROID_FILE__dev_kmsg");
    if (!value || !*value) return;
    char *end;
    errno = 0;
    long fd = strtol(value, &end, 10);
    if (!errno && !*end && fd >= 3 && fd <= INT_MAX)
        dprintf((int)fd, "<3>t860-bpf-supervisor: %s (status=%d)\n", event, status);
}

int main(int argc, char **argv) {
    const char *loader = "/apex/com.android.tethering/bin/netbpfload";
#ifdef SUPERVISOR_HOST_TEST
    if (argc != 2) return 64;
    loader = argv[1];
#else
    (void)argv;
    if (argc != 1) return 64;
#endif
    struct timespec start, now;
    if (clock_gettime(CLOCK_BOOTTIME, &start)) return 1;
    pid_t child = fork();
    if (child < 0) { log_event("fork failed", errno); return 1; }
    if (!child) {
        char *const args[] = {(char *)loader, NULL};
        execv(loader, args);
        log_event("actual loader exec failed", errno);
        _exit(127);
    }
    int finished = 0;
    for (;;) {
        if (!finished) {
            int status = 0;
            pid_t result = waitpid(child, &status, WNOHANG);
            if (result == child) {
                if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
                    log_event("actual loader exited successfully", 0);
                    return 0;
                }
                log_event("actual loader failed; awaiting platform rollback", status);
                finished = 1;
            } else if (result < 0 && errno != EINTR) {
                log_event("waitpid failed; awaiting recovery deadline", errno);
                finished = 1;
            }
        }
        if (clock_gettime(CLOCK_BOOTTIME, &now)) return 1;
        if (now.tv_sec - start.tv_sec >= DEADLINE_SECONDS) {
            log_event("recovery deadline reached without real loader success", 1);
            if (!finished) kill(child, SIGKILL);
            /* No blocking wait: an uninterruptible child cannot defeat deadline. */
            return 1;
        }
        struct timespec pause = {.tv_sec = 0, .tv_nsec = 100000000};
        while (nanosleep(&pause, &pause) && errno == EINTR) {}
    }
}
