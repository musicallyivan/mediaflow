# Media Flow Android

Native Android version of Media Flow.

This is not the web converter. It is an Android app shell with native file
selection, local cache processing, and FFmpeg conversion through FFmpegKit.

## Requirements

- Android Studio
- JDK 17
- Android SDK 35
- 16 KB compatible FFmpegKit dependency from Maven Central or a local
  `app/libs/ffmpeg-kit-16kb.aar`

## Open in Android Studio

1. Open the `android-app` folder.
2. Let Gradle sync.
3. If FFmpegKit cannot be resolved from Maven Central,
   place a compatible AAR at:

   ```text
   app/libs/ffmpeg-kit-16kb.aar
   ```

4. Run the `app` configuration on an emulator or Android device.

## Current Features

- Pick a local file using Android's file picker.
- Convert audio, video, or image locally on the device.
- Choose output format and quality.
- Save results to `Downloads/MediaFlow`.

## Notes

Android conversion is heavier than desktop conversion. Large video files can
take time, heat the device, or fail if the device runs out of memory.
