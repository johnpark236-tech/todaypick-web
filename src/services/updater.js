/**
 * TodayPick In-App Update Service (vc50)
 * Uses official Google Play In-App Updates API via native AppUpdatePlugin.
 */
import { registerPlugin } from '@capacitor/core';
import { ANDROID_VERSION_CODE } from '../config/version.js';

const AppUpdate = registerPlugin('AppUpdate');

class InAppUpdater {
  constructor() {
    this.isDismissedThisSession = false;
    this.isChecking = false;
    this.latestUpdateInfo = null;
  }

  async checkForUpdate() {
    try {
      this.isChecking = true;
      const res = await AppUpdate.checkForUpdate();
      console.log('[InAppUpdater] Check result:', res);
      this.latestUpdateInfo = res;
      return res;
    } catch (err) {
      console.warn('[InAppUpdater] Check note (web or unconfigured):', err.message);
      return { isUpdateAvailable: false, error: err.message };
    } finally {
      this.isChecking = false;
    }
  }

  async startUpdateFlow() {
    try {
      console.log('[InAppUpdater] Triggering Google Play In-App Update flow...');
      const res = await AppUpdate.startUpdate();
      console.log('[InAppUpdater] Start flow result:', res);
      return res;
    } catch (err) {
      console.warn('[InAppUpdater] Start flow note:', err.message);
      return { started: false, error: err.message };
    }
  }

  async completeUpdate() {
    try {
      return await AppUpdate.completeUpdate();
    } catch (err) {
      console.warn('[InAppUpdater] Complete update note:', err.message);
    }
  }

  async checkAndPrompt(domElements) {
    if (this.isDismissedThisSession) return;

    const info = await this.checkForUpdate();
    if (!info) return;

    const isAvailable = Boolean(info.isUpdateAvailable);
    const availableCode = Number(info.availableVersionCode) || 0;
    const installedCode = Number(ANDROID_VERSION_CODE) || 49;

    // Show prompt ONLY if update is available and newer than installed
    if (isAvailable && availableCode > installedCode) {
      if (domElements.dialog) {
        if (domElements.desc) {
          domElements.desc.textContent = `TodayPick 최신 버전(vc${availableCode})이 준비되었습니다. 지금 업데이트하여 최신 기능과 BGM을 만나보세요!`;
        }
        domElements.dialog.style.display = 'flex';
      }
    }
  }
}

export const UpdaterService = new InAppUpdater();