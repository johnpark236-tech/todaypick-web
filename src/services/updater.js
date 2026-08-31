/**
 * TodayPick In-App Update Service (vc51)
 * Uses the official Google Play In-App Updates API through AppUpdatePlugin.
 */
import { Capacitor, registerPlugin } from '@capacitor/core';
import { ANDROID_VERSION_CODE } from '../config/version.js';

const AppUpdate = registerPlugin('AppUpdate');

class InAppUpdater {
  constructor() {
    this.isDismissedThisSession = false;
    this.isChecking = false;
    this.latestUpdateInfo = null;
    this.updateDownloaded = false;
    this.listenerRegistered = false;
    this.isAndroidNative = Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android';
  }

  async ensureListeners(domElements) {
    if (this.listenerRegistered || !this.isAndroidNative || !AppUpdate.addListener) return;
    this.listenerRegistered = true;
    await AppUpdate.addListener('onUpdateDownloaded', () => {
      this.updateDownloaded = true;
      if (domElements?.desc) {
        domElements.desc.textContent = '업데이트 다운로드가 완료되었습니다. 다시 시작하면 최신 버전이 적용됩니다.';
      }
      if (domElements?.dialog) {
        domElements.dialog.style.display = 'flex';
      }
      console.log('[InAppUpdater] Flexible update downloaded.');
    });
  }

  async checkForUpdate() {
    if (!this.isAndroidNative) {
      return {
        isUpdateAvailable: false,
        installedVersionCode: ANDROID_VERSION_CODE,
        skippedReason: 'ANDROID_NATIVE_ONLY'
      };
    }

    try {
      this.isChecking = true;
      const res = await AppUpdate.checkForUpdate();
      console.log('[InAppUpdater] Check result:', res);
      this.latestUpdateInfo = res;
      return res;
    } catch (err) {
      console.warn('[InAppUpdater] Check note:', err.message);
      return {
        isUpdateAvailable: false,
        installedVersionCode: ANDROID_VERSION_CODE,
        error: err.message
      };
    } finally {
      this.isChecking = false;
    }
  }

  async startUpdateFlow() {
    if (!this.isAndroidNative) {
      return { started: false, skippedReason: 'ANDROID_NATIVE_ONLY' };
    }

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
    if (!this.isAndroidNative) {
      return { completed: false, skippedReason: 'ANDROID_NATIVE_ONLY' };
    }

    try {
      const res = await AppUpdate.completeUpdate();
      console.log('[InAppUpdater] Complete update result:', res);
      return res;
    } catch (err) {
      console.warn('[InAppUpdater] Complete update note:', err.message);
      return { completed: false, error: err.message };
    }
  }

  async checkAndPrompt(domElements) {
    if (this.isDismissedThisSession) return;
    await this.ensureListeners(domElements);

    const info = await this.checkForUpdate();
    if (!info) return;

    const isAvailable = Boolean(info.isUpdateAvailable);
    const availableCode = Number(info.availableVersionCode) || 0;
    const installedCode = Number(info.installedVersionCode || ANDROID_VERSION_CODE) || 51;

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
