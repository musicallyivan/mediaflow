package com.musicallyivan.mediaflow;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import com.arthenica.ffmpegkit.FFmpegKit;
import com.arthenica.ffmpegkit.ReturnCode;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int PICK_FILE_REQUEST = 1001;

    private final String[] modes = {"Audio", "Video", "Imagen"};
    private final String[] audioFormats = {"mp3", "m4a", "wav", "flac", "ogg"};
    private final String[] videoFormats = {"mp4", "webm", "mov", "mkv"};
    private final String[] imageFormats = {"png", "jpg", "webp", "bmp"};
    private final String[] qualities = {"Equilibrada", "Archivo pequeno", "Alta calidad"};

    private Uri selectedUri;
    private String selectedName;
    private Spinner modeSpinner;
    private Spinner formatSpinner;
    private Spinner qualitySpinner;
    private TextView fileLabel;
    private TextView statusLabel;
    private ProgressBar progressBar;
    private Button convertButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildLayout());
        updateFormats(0);
    }

    private View buildLayout() {
        ScrollView scrollView = new ScrollView(this);
        scrollView.setFillViewport(true);
        scrollView.setBackgroundColor(Color.rgb(243, 246, 248));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(22), dp(28), dp(22), dp(28));
        scrollView.addView(root);

        TextView title = new TextView(this);
        title.setText("Media Flow");
        title.setTextColor(Color.rgb(24, 32, 47));
        title.setTextSize(34);
        title.setTypeface(null, 1);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Convierte audio, video e imagen localmente en Android.");
        subtitle.setTextColor(Color.rgb(93, 102, 120));
        subtitle.setTextSize(17);
        subtitle.setPadding(0, dp(8), 0, dp(24));
        root.addView(subtitle);

        Button pickButton = primaryButton("Seleccionar archivo");
        pickButton.setOnClickListener(v -> openFilePicker());
        root.addView(pickButton);

        fileLabel = label("Ningun archivo seleccionado.");
        fileLabel.setPadding(0, dp(16), 0, dp(16));
        root.addView(fileLabel);

        modeSpinner = spinner(modes);
        root.addView(sectionLabel("Tipo"));
        root.addView(modeSpinner);
        modeSpinner.setOnItemSelectedListener(new SimpleItemSelectedListener(position -> updateFormats(position)));

        formatSpinner = spinner(audioFormats);
        root.addView(sectionLabel("Formato"));
        root.addView(formatSpinner);

        qualitySpinner = spinner(qualities);
        root.addView(sectionLabel("Calidad"));
        root.addView(qualitySpinner);

        convertButton = primaryButton("Convertir");
        convertButton.setOnClickListener(v -> convertSelectedFile());
        root.addView(convertButton);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setIndeterminate(false);
        progressBar.setMax(100);
        progressBar.setProgress(0);
        progressBar.setPadding(0, dp(24), 0, dp(8));
        root.addView(progressBar);

        statusLabel = label("Listo.");
        root.addView(statusLabel);

        TextView note = label("Los resultados se guardan en Descargas/MediaFlow. Los archivos grandes pueden tardar bastante.");
        note.setPadding(0, dp(24), 0, 0);
        root.addView(note);

        return scrollView;
    }

    private Button primaryButton(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextColor(Color.WHITE);
        button.setTextSize(16);
        button.setAllCaps(false);
        button.setBackgroundColor(Color.rgb(23, 122, 115));
        button.setPadding(dp(14), dp(10), dp(14), dp(10));
        return button;
    }

    private TextView sectionLabel(String text) {
        TextView label = label(text);
        label.setTypeface(null, 1);
        label.setPadding(0, dp(14), 0, dp(6));
        return label;
    }

    private TextView label(String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTextColor(Color.rgb(93, 102, 120));
        label.setTextSize(15);
        label.setGravity(Gravity.START);
        return label;
    }

    private Spinner spinner(String[] values) {
        Spinner spinner = new Spinner(this);
        spinner.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values));
        return spinner;
    }

    private void updateFormats(int modePosition) {
        String[] formats = modePosition == 1 ? videoFormats : modePosition == 2 ? imageFormats : audioFormats;
        if (formatSpinner != null) {
            formatSpinner.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, formats));
        }
    }

    private void openFilePicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        startActivityForResult(intent, PICK_FILE_REQUEST);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_FILE_REQUEST && resultCode == RESULT_OK && data != null) {
            selectedUri = data.getData();
            selectedName = getDisplayName(selectedUri);
            fileLabel.setText(selectedName);
            statusLabel.setText("Archivo seleccionado.");
        }
    }

    private void convertSelectedFile() {
        if (selectedUri == null) {
            Toast.makeText(this, "Selecciona un archivo primero.", Toast.LENGTH_SHORT).show();
            return;
        }

        convertButton.setEnabled(false);
        progressBar.setIndeterminate(true);
        statusLabel.setText("Preparando archivo...");

        new Thread(() -> {
            try {
                File input = copyUriToCache(selectedUri, selectedName);
                String format = formatSpinner.getSelectedItem().toString();
                String outputName = baseName(selectedName) + "." + format;
                File output = new File(getCacheDir(), outputName);
                String command = buildCommand(input, output, format);

                runOnUiThread(() -> statusLabel.setText("Convirtiendo..."));
                FFmpegKit.executeAsync(command, session -> {
                    ReturnCode code = session.getReturnCode();
                    if (ReturnCode.isSuccess(code)) {
                        try {
                            Uri saved = saveToDownloads(output, outputName, format);
                            runOnUiThread(() -> {
                                progressBar.setIndeterminate(false);
                                progressBar.setProgress(100);
                                statusLabel.setText("Conversion completada: " + saved);
                                convertButton.setEnabled(true);
                            });
                        } catch (Exception error) {
                            showFailure(error);
                        }
                    } else {
                        showFailure(new IllegalStateException("FFmpeg fallo con codigo " + code));
                    }
                });
            } catch (Exception error) {
                showFailure(error);
            }
        }).start();
    }

    private String buildCommand(File input, File output, String format) {
        String mode = modeSpinner.getSelectedItem().toString();
        String quality = qualitySpinner.getSelectedItem().toString();
        StringBuilder command = new StringBuilder();
        command.append("-y -i ").append(quote(input.getAbsolutePath())).append(" ");

        if ("Audio".equals(mode)) {
            command.append("-vn ");
            if ("m4a".equals(format)) {
                command.append("-c:a aac ");
            }
            if ("mp3".equals(format) || "m4a".equals(format) || "ogg".equals(format)) {
                command.append("-b:a ").append(audioBitrate(quality)).append(" ");
            }
        }

        if ("Video".equals(mode)) {
            if ("mp4".equals(format) || "mov".equals(format) || "mkv".equals(format)) {
                command.append("-pix_fmt yuv420p ");
            }
            if ("Archivo pequeno".equals(quality)) {
                command.append("-vf scale='min(1280,iw)':-2 ");
            }
        }

        if ("Imagen".equals(mode)) {
            if ("jpg".equals(format)) {
                command.append("-q:v ").append("Alta calidad".equals(quality) ? "2 " : "Archivo pequeno".equals(quality) ? "9 " : "5 ");
            }
            if ("webp".equals(format)) {
                command.append("-quality ").append("Alta calidad".equals(quality) ? "90 " : "Archivo pequeno".equals(quality) ? "65 " : "80 ");
            }
        }

        command.append(quote(output.getAbsolutePath()));
        return command.toString();
    }

    private String audioBitrate(String quality) {
        if ("Alta calidad".equals(quality)) {
            return "256k";
        }
        if ("Archivo pequeno".equals(quality)) {
            return "128k";
        }
        return "192k";
    }

    private File copyUriToCache(Uri uri, String name) throws Exception {
        File target = new File(getCacheDir(), "input-" + System.currentTimeMillis() + "-" + sanitize(name));
        try (InputStream in = getContentResolver().openInputStream(uri);
             OutputStream out = new FileOutputStream(target)) {
            if (in == null) {
                throw new IllegalStateException("No se pudo abrir el archivo.");
            }
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
        }
        return target;
    }

    private Uri saveToDownloads(File file, String name, String format) throws Exception {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, name);
        values.put(MediaStore.Downloads.MIME_TYPE, mimeType(format));
        values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/MediaFlow");

        ContentResolver resolver = getContentResolver();
        Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) {
            throw new IllegalStateException("No se pudo crear el archivo de salida.");
        }

        try (InputStream in = new FileInputStream(file);
             OutputStream out = resolver.openOutputStream(uri)) {
            if (out == null) {
                throw new IllegalStateException("No se pudo escribir el archivo de salida.");
            }
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
        }
        return uri;
    }

    private String getDisplayName(Uri uri) {
        try (Cursor cursor = getContentResolver().query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) {
                    return cursor.getString(index);
                }
            }
        }
        return "archivo";
    }

    private String baseName(String name) {
        int dot = name.lastIndexOf('.');
        return sanitize(dot > 0 ? name.substring(0, dot) : name);
    }

    private String sanitize(String value) {
        return value.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private String quote(String value) {
        return "\"" + value.replace("\"", "\\\"") + "\"";
    }

    private String mimeType(String format) {
        switch (format.toLowerCase(Locale.ROOT)) {
            case "mp3": return "audio/mpeg";
            case "m4a": return "audio/mp4";
            case "wav": return "audio/wav";
            case "flac": return "audio/flac";
            case "ogg": return "audio/ogg";
            case "mp4": return "video/mp4";
            case "webm": return "video/webm";
            case "mov": return "video/quicktime";
            case "mkv": return "video/x-matroska";
            case "png": return "image/png";
            case "jpg": return "image/jpeg";
            case "webp": return "image/webp";
            case "bmp": return "image/bmp";
            default: return "application/octet-stream";
        }
    }

    private void showFailure(Exception error) {
        runOnUiThread(() -> {
            progressBar.setIndeterminate(false);
            progressBar.setProgress(0);
            statusLabel.setText("No se pudo convertir: " + error.getMessage());
            convertButton.setEnabled(true);
        });
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }
}
