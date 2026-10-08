# Independent recovery entry appended only by the A70 restore builder.
# It restores the entire known stable snapshot, never individual old binaries.
A71_OPERATION_BANNER='RESTORE EXACT A70 STABLE ONE UI 8.5 SNAPSHOT; this is not the upgrade ZIP'
check_source_system() {
    # A half-written SYSTEM must not be required to mount for full restoration.
    SYSTEM_ALREADY_VERIFIED=0
}
upgrade_main() {
    check_equal 'Restore mode' "$(config mode)" A70_STABLE_SNAPSHOT
    check_equal 'Fixed restore SYSTEM' "$(config system.sha256)" @@RESTORE_SYSTEM_SHA@@
    check_equal 'Fixed restore PRODUCT' "$(config product.sha256)" @@RESTORE_PRODUCT_SHA@@
    a71_upgrade_transaction
}
