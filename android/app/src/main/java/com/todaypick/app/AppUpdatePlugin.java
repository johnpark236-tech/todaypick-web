package com.todaypick.app;

import android.app.Activity;
import android.content.IntentSender;
import android.content.pm.PackageInfo;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.google.android.play.core.appupdate.AppUpdateInfo;
import com.google.android.play.core.appupdate.AppUpdateManager;
import com.google.android.play.core.appupdate.AppUpdateManagerFactory;
import com.google.android.play.core.appupdate.AppUpdateOptions;
import com.google.android.play.core.install.InstallStateUpdatedListener;
import com.google.android.play.core.install.model.AppUpdateType;
import com.google.android.play.core.install.model.InstallStatus;
import com.google.android.play.core.install.model.UpdateAvailability;

@CapacitorPlugin(name = "AppUpdate")
public class AppUpdatePlugin extends Plugin {
    private static final String TAG = "AppUpdatePlugin";
    private AppUpdateManager appUpdateManager;
    private AppUpdateInfo currentUpdateInfo;
    private InstallStateUpdatedListener installStateUpdatedListener;

    @Override
    public void load() {
        super.load();
        appUpdateManager = AppUpdateManagerFactory.create(getContext());
        
        installStateUpdatedListener = state -> {
            if (state.installStatus() == InstallStatus.DOWNLOADED) {
                Log.d(TAG, "In-App Update downloaded! Ready for completion.");
                JSObject ret = new JSObject();
                ret.put("status", "DOWNLOADED");
                notifyListeners("onUpdateDownloaded", ret);
            }
        };
        appUpdateManager.registerListener(installStateUpdatedListener);
    }

    @Override
    protected void handleOnDestroy() {
        super.handleOnDestroy();
        if (appUpdateManager != null && installStateUpdatedListener != null) {
            appUpdateManager.unregisterListener(installStateUpdatedListener);
        }
    }

    @PluginMethod
    public void checkForUpdate(PluginCall call) {
        if (appUpdateManager == null) {
            call.reject("AppUpdateManager not initialized");
            return;
        }

        appUpdateManager.getAppUpdateInfo().addOnSuccessListener(appUpdateInfo -> {
            currentUpdateInfo = appUpdateInfo;
            int availability = appUpdateInfo.updateAvailability();
            int availableVersionCode = appUpdateInfo.availableVersionCode();
            boolean isAvailable = (availability == UpdateAvailability.UPDATE_AVAILABLE ||
                                   availability == UpdateAvailability.DEVELOPER_TRIGGERED_UPDATE_IN_PROGRESS);

            JSObject ret = new JSObject();
            ret.put("updateAvailability", availability);
            ret.put("availableVersionCode", availableVersionCode);
            ret.put("installedVersionCode", getInstalledVersionCode());
            ret.put("isUpdateAvailable", isAvailable);
            ret.put("isImmediateAllowed", appUpdateInfo.isUpdateTypeAllowed(AppUpdateType.IMMEDIATE));
            ret.put("isFlexibleAllowed", appUpdateInfo.isUpdateTypeAllowed(AppUpdateType.FLEXIBLE));

            Log.d(TAG, "checkForUpdate: availability=" + availability + ", availableVersionCode=" + availableVersionCode);
            call.resolve(ret);
        }).addOnFailureListener(e -> {
            Log.w(TAG, "checkForUpdate failed: " + e.getMessage());
            JSObject ret = new JSObject();
            ret.put("isUpdateAvailable", false);
            ret.put("error", e.getMessage());
            call.resolve(ret);
        });
    }

    @PluginMethod
    public void startUpdate(PluginCall call) {
        if (appUpdateManager == null || currentUpdateInfo == null) {
            call.reject("Update info not available. Call checkForUpdate first.");
            return;
        }

        Activity activity = getActivity();
        if (activity == null) {
            call.reject("Activity is null");
            return;
        }

        int updateType = currentUpdateInfo.isUpdateTypeAllowed(AppUpdateType.FLEXIBLE) 
                ? AppUpdateType.FLEXIBLE 
                : AppUpdateType.IMMEDIATE;
        if (!currentUpdateInfo.isUpdateTypeAllowed(updateType)) {
            call.reject("No allowed Google Play update type is available");
            return;
        }

        try {
            appUpdateManager.startUpdateFlowForResult(
                currentUpdateInfo,
                activity,
                AppUpdateOptions.newBuilder(updateType).build(),
                1001
            );
            JSObject ret = new JSObject();
            ret.put("started", true);
            ret.put("type", updateType == AppUpdateType.FLEXIBLE ? "FLEXIBLE" : "IMMEDIATE");
            call.resolve(ret);
        } catch (IntentSender.SendIntentException e) {
            Log.e(TAG, "startUpdateFlowForResult failed", e);
            call.reject("Failed to start update flow: " + e.getMessage());
        }
    }

    @PluginMethod
    public void completeUpdate(PluginCall call) {
        if (appUpdateManager != null) {
            appUpdateManager.completeUpdate().addOnSuccessListener(unused -> {
                JSObject ret = new JSObject();
                ret.put("completed", true);
                call.resolve(ret);
            }).addOnFailureListener(e -> {
                Log.w(TAG, "completeUpdate failed: " + e.getMessage());
                call.reject("completeUpdate failed: " + e.getMessage());
            });
        } else {
            call.reject("AppUpdateManager is null");
        }
    }

    @Override
    protected void handleOnResume() {
        super.handleOnResume();
        if (appUpdateManager == null) return;
        appUpdateManager.getAppUpdateInfo().addOnSuccessListener(appUpdateInfo -> {
            if (appUpdateInfo.updateAvailability() == UpdateAvailability.DEVELOPER_TRIGGERED_UPDATE_IN_PROGRESS) {
                Activity activity = getActivity();
                if (activity == null) return;
                try {
                    appUpdateManager.startUpdateFlowForResult(
                        appUpdateInfo,
                        activity,
                        AppUpdateOptions.newBuilder(AppUpdateType.IMMEDIATE).build(),
                        1001
                    );
                } catch (IntentSender.SendIntentException e) {
                    Log.e(TAG, "resume update flow failed", e);
                }
            }
        });
    }

    private long getInstalledVersionCode() {
        try {
            PackageInfo info = getContext().getPackageManager().getPackageInfo(getContext().getPackageName(), 0);
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.P) {
                return info.getLongVersionCode();
            }
            return info.versionCode;
        } catch (Exception e) {
            Log.w(TAG, "installed version check failed: " + e.getMessage());
            return -1;
        }
    }
}
