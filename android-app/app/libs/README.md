# FFmpegKit AAR

This project uses FFmpegKit to run local FFmpeg conversions on Android.

`app/build.gradle` first looks for:

```text
app/libs/ffmpeg-kit-full.aar
```

If that file is not present, Gradle tries the Maven dependency:

```gradle
com.arthenica:ffmpeg-kit-full:6.0-2
```

FFmpegKit has been officially retired, so keeping a local AAR is recommended
for reproducible builds.
