# FFmpegKit 16 KB AAR

This project uses a 16 KB page-size compatible FFmpegKit build to run local
FFmpeg conversions on Android.

`app/build.gradle` first looks for:

```text
app/libs/ffmpeg-kit-16kb.aar
```

If that file is not present, Gradle tries the Maven dependency:

```gradle
com.moizhassan.ffmpeg:ffmpeg-kit-16kb:6.0.0
```

The original FFmpegKit packages are retired and are not 16 KB page-size
compatible. Keeping a local 16 KB AAR is recommended for reproducible builds.
