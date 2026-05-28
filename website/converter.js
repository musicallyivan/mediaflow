import { FFmpeg } from "https://cdn.jsdelivr.net/npm/@ffmpeg/ffmpeg@0.12.10/dist/esm/index.js";
import { fetchFile, toBlobURL } from "https://cdn.jsdelivr.net/npm/@ffmpeg/util@0.12.1/dist/esm/index.js";

const formatsByMode = {
  audio: ["mp3", "m4a", "wav", "flac", "ogg"],
  video: ["mp4", "webm", "mov", "mkv"],
  image: ["png", "jpg", "webp", "bmp"],
};

const mimeByFormat = {
  mp3: "audio/mpeg",
  m4a: "audio/mp4",
  wav: "audio/wav",
  flac: "audio/flac",
  ogg: "audio/ogg",
  mp4: "video/mp4",
  webm: "video/webm",
  mov: "video/quicktime",
  mkv: "video/x-matroska",
  png: "image/png",
  jpg: "image/jpeg",
  webp: "image/webp",
  bmp: "image/bmp",
};

const fileInput = document.querySelector("#fileInput");
const dropZone = document.querySelector("#dropZone");
const selectedFile = document.querySelector("#selectedFile");
const modeSelect = document.querySelector("#modeSelect");
const formatSelect = document.querySelector("#formatSelect");
const qualitySelect = document.querySelector("#qualitySelect");
const form = document.querySelector("#converterForm");
const convertButton = document.querySelector("#convertButton");
const downloadResult = document.querySelector("#downloadResult");
const statusText = document.querySelector("#statusText");
const progressText = document.querySelector("#progressText");
const progressBar = document.querySelector("#progressBar");

const ffmpeg = new FFmpeg();
let ffmpegLoaded = false;
let lastDownloadUrl = null;

function setStatus(message, progress = null) {
  statusText.textContent = message;

  if (progress !== null) {
    const percentage = Math.max(0, Math.min(100, Math.round(progress)));
    progressBar.value = percentage;
    progressText.textContent = `${percentage}%`;
  }
}

function formatBytes(bytes) {
  if (!bytes) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function updateFormats() {
  const formats = formatsByMode[modeSelect.value];
  formatSelect.replaceChildren(
    ...formats.map((format) => {
      const option = document.createElement("option");
      option.value = format;
      option.textContent = format.toUpperCase();
      return option;
    }),
  );
}

function updateSelectedFile() {
  const file = fileInput.files?.[0];

  if (!file) {
    selectedFile.hidden = true;
    selectedFile.textContent = "";
    return;
  }

  selectedFile.hidden = false;
  selectedFile.textContent = `${file.name} · ${formatBytes(file.size)}`;
}

async function loadFFmpeg() {
  if (ffmpegLoaded) {
    return;
  }

  setStatus("Cargando motor de conversion...", 5);
  const ffmpegURL = "https://cdn.jsdelivr.net/npm/@ffmpeg/ffmpeg@0.12.10/dist/esm";
  const baseURL = "https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/umd";

  ffmpeg.on("progress", ({ progress }) => {
    setStatus("Convirtiendo...", progress * 100);
  });

  ffmpeg.on("log", ({ message }) => {
    if (message.toLowerCase().includes("error")) {
      console.debug(message);
    }
  });

  await ffmpeg.load({
    classWorkerURL: await toBlobURL(`${ffmpegURL}/worker.js`, "text/javascript"),
    coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, "text/javascript"),
    wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, "application/wasm"),
  });

  ffmpegLoaded = true;
  setStatus("Motor listo.", 10);
}

function getOutputName(inputName, format) {
  const cleanName = inputName.replace(/\.[^.]+$/, "");
  return `${cleanName || "media-flow-output"}.${format}`;
}

function buildArgs(inputName, outputName, mode, format, quality) {
  const args = ["-i", inputName];

  if (mode === "audio") {
    args.push("-vn");

    if (format === "m4a") {
      args.push("-c:a", "aac");
    }

    if (format === "mp3" || format === "m4a" || format === "ogg") {
      const bitrate = quality === "high" ? "256k" : quality === "small" ? "128k" : "192k";
      args.push("-b:a", bitrate);
    }
  }

  if (mode === "video") {
    if (format === "mp4" || format === "mov" || format === "mkv") {
      args.push("-pix_fmt", "yuv420p");
    }

    if (quality === "small") {
      args.push("-vf", "scale='min(1280,iw)':-2");
    }
  }

  if (mode === "image") {
    if (format === "jpg") {
      const q = quality === "high" ? "2" : quality === "small" ? "9" : "5";
      args.push("-q:v", q);
    }

    if (format === "webp") {
      const q = quality === "high" ? "90" : quality === "small" ? "65" : "80";
      args.push("-quality", q);
    }
  }

  args.push(outputName);
  return args;
}

async function convertFile(event) {
  event.preventDefault();

  const file = fileInput.files?.[0];

  if (!file) {
    setStatus("Selecciona un archivo primero.", 0);
    return;
  }

  convertButton.disabled = true;
  downloadResult.hidden = true;

  if (lastDownloadUrl) {
    URL.revokeObjectURL(lastDownloadUrl);
    lastDownloadUrl = null;
  }

  try {
    await loadFFmpeg();

    const mode = modeSelect.value;
    const format = formatSelect.value;
    const inputName = `input-${Date.now()}-${file.name.replace(/[^\w.-]/g, "_")}`;
    const outputName = getOutputName(file.name, format);
    const args = buildArgs(inputName, outputName, mode, format, qualitySelect.value);

    setStatus("Preparando archivo...", 12);
    await ffmpeg.writeFile(inputName, await fetchFile(file));

    setStatus("Convirtiendo...", 15);
    await ffmpeg.exec(args);

    const data = await ffmpeg.readFile(outputName);
    const blob = new Blob([data.buffer], { type: mimeByFormat[format] || "application/octet-stream" });
    lastDownloadUrl = URL.createObjectURL(blob);

    downloadResult.href = lastDownloadUrl;
    downloadResult.download = outputName;
    downloadResult.hidden = false;
    setStatus("Conversion completada.", 100);

    await ffmpeg.deleteFile(inputName);
    await ffmpeg.deleteFile(outputName);
  } catch (error) {
    console.error(error);
    setStatus("No se pudo convertir este archivo. Prueba otro formato o usa la app de escritorio.", 0);
  } finally {
    convertButton.disabled = false;
  }
}

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("is-dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("is-dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("is-dragging");

  if (event.dataTransfer.files.length) {
    fileInput.files = event.dataTransfer.files;
    updateSelectedFile();
  }
});

modeSelect.addEventListener("change", updateFormats);
fileInput.addEventListener("change", updateSelectedFile);
form.addEventListener("submit", convertFile);

updateFormats();
