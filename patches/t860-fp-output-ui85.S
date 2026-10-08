// S9 output dispatch, rebuilt for each pinned donor. No stack or frame changes.
// Entered by direct B from the original strncmp callsite. The parent frame's
// signed return address remains in its original stack slot.
.text
.macro PREFIX_BYTE off, value, fallback
    ldrb w3, [x0, #\off]
    cmp w3, #\value
    b.ne \fallback
.endm

.macro FP_OUTPUT name, resume, mask
    .p2align 4
    .global \name
    .type \name, %function
\name:
    bti c
    PREFIX_BYTE 0,  0x46, 9f // F
    PREFIX_BYTE 1,  0x50, 9f // P
    PREFIX_BYTE 2,  0x20, 9f // space
    PREFIX_BYTE 3,  0x4d, 9f // M
    PREFIX_BYTE 4,  0x61, 9f // a
    PREFIX_BYTE 5,  0x73, 9f // s
    PREFIX_BYTE 6,  0x6b, 9f // k
    PREFIX_BYTE 7,  0x76, 9f // v
    PREFIX_BYTE 8,  0x69, 9f // i
    PREFIX_BYTE 9,  0x65, 9f // e
    PREFIX_BYTE 10, 0x77, 9f // w
    b \mask
9:
    // ADR cannot reach the original return PC from the appended RX segment.
    // ADRP+ADD reconstructs the original BL's LR with PIE-relative addressing.
    adrp x30, \resume
    add x30, x30, :lo12:\resume
    b t860_strncmp
    .size \name, .-\name
.endm

FP_OUTPUT t860_fp_output_1, t860_resume_1, t860_mask_1
FP_OUTPUT t860_fp_output_2, t860_resume_2, t860_mask_2
.section .note.GNU-stack,"",%progbits
