package com.todaypick.app;

import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.util.Log;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.json.JSONObject;

@CapacitorPlugin(name = "TodayPickAudio")
public class TodayPickAudioPlugin extends Plugin {
    private static final String TAG = "TodayPickAudio";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final List<Track> playlist = new ArrayList<>();
    private MediaPlayer player;
    private int currentIndex = 0;
    private float bgmVolume = 0.55f;
    private boolean bgmEnabled = true;

    @Override
    protected void handleOnDestroy() {
        super.handleOnDestroy();
        releasePlayer();
        executor.shutdownNow();
    }

    @PluginMethod
    public void configure(PluginCall call) {
        bgmEnabled = call.getBoolean("enabled", true);
        bgmVolume = clamp(call.getFloat("volume", 0.55f));
        playlist.clear();
        JSArray tracks = call.getArray("tracks");
        if (tracks != null) {
            for (int i = 0; i < tracks.length(); i++) {
                JSONObject obj = tracks.optJSONObject(i);
                if (obj == null) continue;
                Track track = new Track(
                        obj.optString("id", "track_" + i),
                        obj.optString("title", "Track " + (i + 1)),
                        obj.optString("fileName", "track_" + i + ".mp3"),
                        obj.optString("url", "")
                );
                if (!track.url.isEmpty()) playlist.add(track);
            }
        }
        JSObject ret = new JSObject();
        ret.put("configured", true);
        ret.put("trackCount", playlist.size());
        ret.put("volume", bgmVolume);
        ret.put("enabled", bgmEnabled);
        Log.d(TAG, "CONFIGURE trackCount=" + playlist.size() + " volume=" + bgmVolume + " enabled=" + bgmEnabled);
        call.resolve(ret);
    }

    @PluginMethod
    public void playTrack(PluginCall call) {
        if (playlist.isEmpty()) {
            call.reject("PLAYLIST_EMPTY");
            return;
        }
        Integer requested = call.getInt("index");
        if (requested != null && requested >= 0 && requested < playlist.size()) {
            currentIndex = requested;
        }
        bgmEnabled = true;
        prepareAndPlayCurrent(call);
    }

    @PluginMethod
    public void pauseBgm(PluginCall call) {
        bgmEnabled = false;
        if (player != null && player.isPlaying()) player.pause();
        JSObject ret = new JSObject();
        ret.put("paused", true);
        Log.d(TAG, "BGM_OFF pauseBgm");
        call.resolve(ret);
    }

    @PluginMethod
    public void resumeBgm(PluginCall call) {
        bgmEnabled = true;
        if (player != null) {
            player.setVolume(bgmVolume, bgmVolume);
            player.start();
            JSObject ret = new JSObject();
            ret.put("resumed", true);
            Log.d(TAG, "PLAYER_STARTED resume existing index=" + currentIndex + " volume=" + bgmVolume);
            call.resolve(ret);
            return;
        }
        playTrack(call);
    }

    @PluginMethod
    public void stopBgm(PluginCall call) {
        bgmEnabled = false;
        releasePlayer();
        JSObject ret = new JSObject();
        ret.put("stopped", true);
        Log.d(TAG, "BGM_OFF stopBgm");
        call.resolve(ret);
    }

    @PluginMethod
    public void setBgmVolume(PluginCall call) {
        bgmVolume = clamp(call.getFloat("volume", 0.55f));
        if (player != null) player.setVolume(bgmVolume, bgmVolume);
        JSObject ret = new JSObject();
        ret.put("volume", bgmVolume);
        Log.d(TAG, "VOLUME bgm=" + bgmVolume);
        call.resolve(ret);
    }

    @PluginMethod
    public void getBgmState(PluginCall call) {
        JSObject ret = new JSObject();
        ret.put("enabled", bgmEnabled);
        ret.put("volume", bgmVolume);
        ret.put("trackCount", playlist.size());
        ret.put("currentIndex", currentIndex);
        ret.put("playing", player != null && player.isPlaying());
        if (!playlist.isEmpty()) ret.put("title", playlist.get(currentIndex).title);
        call.resolve(ret);
    }

    @PluginMethod
    public void downloadTrack(PluginCall call) {
        Integer requested = call.getInt("index");
        int index = requested == null ? currentIndex : requested;
        if (index < 0 || index >= playlist.size()) {
            call.reject("TRACK_INDEX_INVALID");
            return;
        }
        Track track = playlist.get(index);
        executor.execute(() -> {
            try {
                File file = ensureDownloaded(track);
                JSObject ret = fileResult(track, file);
                call.resolve(ret);
            } catch (Exception e) {
                Log.e(TAG, "DOWNLOAD_FAIL " + track.fileName, e);
                call.reject("DOWNLOAD_FAIL: " + e.getClass().getSimpleName());
            }
        });
    }

    private void prepareAndPlayCurrent(PluginCall call) {
        Track track = playlist.get(currentIndex);
        executor.execute(() -> {
            try {
                File file = ensureDownloaded(track);
                getActivity().runOnUiThread(() -> {
                    try {
                        releasePlayer();
                        player = new MediaPlayer();
                        player.setAudioAttributes(new AudioAttributes.Builder()
                                .setUsage(AudioAttributes.USAGE_MEDIA)
                                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                                .build());
                        player.setDataSource(file.getAbsolutePath());
                        player.setVolume(bgmVolume, bgmVolume);
                        player.setOnCompletionListener(mp -> {
                            Log.d(TAG, "PLAYER_COMPLETED index=" + currentIndex + " title=" + playlist.get(currentIndex).title);
                            currentIndex = (currentIndex + 1) % playlist.size();
                            if (bgmEnabled) prepareAndPlayCurrent(null);
                        });
                        player.setOnPreparedListener(mp -> {
                            Log.d(TAG, "PLAYER_PREPARED index=" + currentIndex + " file=" + file.getAbsolutePath());
                            if (bgmEnabled) {
                                mp.start();
                                Log.d(TAG, "PLAYER_STARTED index=" + currentIndex + " volume=" + bgmVolume);
                            }
                            JSObject ret = fileResult(track, file);
                            ret.put("started", bgmEnabled);
                            ret.put("index", currentIndex);
                            if (call != null) call.resolve(ret);
                        });
                        player.prepareAsync();
                    } catch (Exception e) {
                        Log.e(TAG, "PLAYER_START_FAIL " + track.fileName, e);
                        if (call != null) call.reject("PLAYER_START_FAIL: " + e.getClass().getSimpleName());
                    }
                });
            } catch (Exception e) {
                Log.e(TAG, "DOWNLOAD_OR_PLAY_FAIL " + track.fileName, e);
                if (call != null) call.reject("DOWNLOAD_OR_PLAY_FAIL: " + e.getClass().getSimpleName());
            }
        });
    }

    private File ensureDownloaded(Track track) throws Exception {
        File dir = new File(getContext().getCacheDir(), "todaypick_bgm");
        if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("CACHE_DIR_CREATE_FAIL");
        File file = new File(dir, safeFileName(track.fileName));
        if (file.exists() && file.length() > 10000 && looksLikeMp3(file)) {
            Log.d(TAG, "LOCAL_FILE cached path=" + file.getAbsolutePath() + " bytes=" + file.length());
            return file;
        }

        Log.d(TAG, "DOWNLOAD_START title=" + track.title + " file=" + track.fileName);
        HttpURLConnection conn = (HttpURLConnection) new URL(track.url).openConnection();
        conn.setInstanceFollowRedirects(true);
        conn.setConnectTimeout(20000);
        conn.setReadTimeout(60000);
        conn.setRequestProperty("User-Agent", "TodayPick-Android-Audio/1.0");
        int status = conn.getResponseCode();
        String contentType = conn.getContentType();
        int expectedSize = conn.getContentLength();
        InputStream input = status >= 200 && status < 300 ? conn.getInputStream() : conn.getErrorStream();
        File tmp = new File(dir, file.getName() + ".tmp");
        long total = 0;
        byte[] buffer = new byte[8192];
        try (InputStream in = input; FileOutputStream out = new FileOutputStream(tmp)) {
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
                total += read;
            }
        } finally {
            conn.disconnect();
        }
        if (status < 200 || status >= 300) throw new IllegalStateException("HTTP_STATUS_" + status);
        if (total <= 10000 || !looksLikeMp3(tmp)) throw new IllegalStateException("NOT_MP3_OR_TOO_SMALL");
        if (file.exists() && !file.delete()) throw new IllegalStateException("CACHE_REPLACE_FAIL");
        if (!tmp.renameTo(file)) throw new IllegalStateException("CACHE_RENAME_FAIL");
        Log.d(TAG, "DOWNLOAD_COMPLETE status=" + status + " bytes=" + total + " expected=" + expectedSize + " type=" + contentType + " path=" + file.getAbsolutePath());
        return file;
    }

    private JSObject fileResult(Track track, File file) {
        JSObject ret = new JSObject();
        ret.put("HTTP_STATUS", "CACHE_OR_200");
        ret.put("LOCAL_PATH", file.getAbsolutePath());
        ret.put("FILE_EXISTS", file.exists());
        ret.put("FILE_SIZE", file.length());
        ret.put("title", track.title);
        ret.put("fileName", track.fileName);
        return ret;
    }

    private boolean looksLikeMp3(File file) {
        try (InputStream in = new java.io.FileInputStream(file)) {
            byte[] h = new byte[3];
            int n = in.read(h);
            if (n < 3) return false;
            boolean id3 = h[0] == 'I' && h[1] == 'D' && h[2] == '3';
            boolean frame = (h[0] & 0xFF) == 0xFF && (h[1] & 0xE0) == 0xE0;
            return id3 || frame;
        } catch (Exception e) {
            return false;
        }
    }

    private void releasePlayer() {
        if (player == null) return;
        try {
            if (player.isPlaying()) player.stop();
            player.reset();
            player.release();
        } catch (Exception ignored) {
        } finally {
            player = null;
        }
    }

    private float clamp(Float value) {
        float v = value == null ? 0.55f : value;
        return Math.max(0f, Math.min(1f, v));
    }

    private String safeFileName(String fileName) throws Exception {
        String base = fileName == null ? "track.mp3" : fileName.replaceAll("[^A-Za-z0-9._-]", "_");
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] hash = md.digest(base.getBytes("UTF-8"));
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 4; i++) sb.append(String.format("%02x", hash[i]));
        return sb + "_" + base;
    }

    private static class Track {
        final String id;
        final String title;
        final String fileName;
        final String url;

        Track(String id, String title, String fileName, String url) {
            this.id = id;
            this.title = title;
            this.fileName = fileName;
            this.url = url;
        }
    }
}
