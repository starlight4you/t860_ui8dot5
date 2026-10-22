package com.samsung.android.hardware.secinputdev.hal;

import android.os.Build;
import android.util.Log;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** The T860 HIDL 1.2 adapter lacks these two original Wacom sysfs properties. */
public final class T860SpenLegacy {
    public static final int NOT_HANDLED = -1000;

    private T860SpenLegacy() {}

    public static int set(String property, String value) {
        if (!"SM-T860".equals(Build.MODEL)) return NOT_HANDLED;
        final String path;
        final int maximum;
        if ("BLE_CHARGING".equals(property)) {
            path = "/sys/class/sec/sec_epen/epen_ble_charging_mode";
            maximum = 8;
        } else if ("EPEN_SAVING".equals(property)) {
            path = "/sys/class/sec/sec_epen/epen_saving_mode";
            maximum = 1;
        } else {
            return NOT_HANDLED;
        }
        final int number;
        try {
            number = Integer.parseInt(value);
        } catch (NumberFormatException error) {
            return -2;
        }
        if (number < 0 || number > maximum || !Integer.toString(number).equals(value)) {
            return -2;
        }
        try (FileOutputStream stream = new FileOutputStream(path)) {
            stream.write(value.getBytes(StandardCharsets.US_ASCII));
        } catch (IOException | SecurityException error) {
            Log.e("T860SpenCompat", "Legacy write failed: " + property, error);
            return -1;
        }
        Log.i("T860SpenCompat", "Legacy write accepted: " + property + "=" + value);
        return 0;
    }
}
