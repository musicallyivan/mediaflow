import Foundation
import Combine
#if canImport(ffmpegkit)
import ffmpegkit
#endif

enum MediaMode: String, CaseIterable, Identifiable {
    case audio = "Audio"
    case video = "Video"
    case image = "Imagen"
    
    var id: String { rawValue }
    
    var defaultFormats: [String] {
        switch self {
        case .audio:
            return ["mp3", "m4a", "wav", "flac", "ogg", "opus", "aac"]
        case .video:
            return ["mp4", "webm", "mov", "mkv", "gif", "avi"]
        case .image:
            return ["png", "jpg", "webp", "bmp", "tiff"]
        }
    }
}

enum QualityLevel: String, CaseIterable, Identifiable {
    case balanced = "Equilibrada"
    case smallFile = "Archivo pequeño"
    case highQuality = "Alta calidad"
    
    var id: String { rawValue }
}

@MainActor
class ConverterEngine: ObservableObject {
    @Published var selectedMode: MediaMode = .audio {
        didSet {
            if !selectedMode.defaultFormats.contains(selectedFormat) {
                selectedFormat = selectedMode.defaultFormats.first ?? "mp3"
            }
        }
    }
    @Published var selectedFormat: String = "mp3"
    @Published var selectedQuality: QualityLevel = .balanced
    
    @Published var selectedFileURL: URL?
    @Published var selectedFileName: String = ""
    @Published var selectedFileSize: String = ""
    
    @Published var isConverting: Bool = false
    @Published var progress: Double = 0.0
    @Published var statusMessage: String = "Listo para convertir."
    @Published var outputFileURL: URL?
    @Published var errorMessage: String?
    @Published var showShareSheet: Bool = false
    
    init() {
        setupCallbacks()
    }
    
    private func setupCallbacks() {
        #if canImport(ffmpegkit)
        FFmpegKitConfig.enableStatisticsCallback { [weak self] statistics in
            guard let stats = statistics else { return }
            let timeInMs = stats.getTime()
            DispatchQueue.main.async {
                if let self = self, self.isConverting {
                    // Update indeterminate progress feel or estimated time
                    if self.progress < 0.90 {
                        self.progress += 0.05
                    }
                    self.statusMessage = "Procesando multimedia (\(Int(timeInMs / 1000))s)..."
                }
            }
        }
        #endif
    }
    
    func selectFile(url: URL) {
        let isSecurityScoped = url.startAccessingSecurityScopedResource()
        defer {
            if isSecurityScoped {
                url.stopAccessingSecurityScopedResource()
            }
        }
        
        selectedFileURL = url
        selectedFileName = url.lastPathComponent
        
        if let attributes = try? FileManager.default.attributesOfItem(atPath: url.path),
           let size = attributes[.size] as? Int64 {
            selectedFileSize = ByteCountFormatter.string(fromByteCount: size, countStyle: .file)
        } else {
            selectedFileSize = ""
        }
        
        outputFileURL = nil
        errorMessage = nil
        progress = 0.0
        statusMessage = "Archivo cargado: \(selectedFileName)"
        
        // Auto-detect mode if possible
        let ext = url.pathExtension.lowercased()
        if ["mp3", "wav", "m4a", "flac", "ogg", "aac", "aiff", "opus"].contains(ext) {
            selectedMode = .audio
        } else if ["mp4", "mov", "webm", "mkv", "avi", "m4v"].contains(ext) {
            selectedMode = .video
        } else if ["png", "jpg", "jpeg", "webp", "bmp", "heic", "tiff"].contains(ext) {
            selectedMode = .image
        }
        selectedFormat = selectedMode.defaultFormats.first ?? "mp3"
    }
    
    func reset() {
        selectedFileURL = nil
        selectedFileName = ""
        selectedFileSize = ""
        outputFileURL = nil
        errorMessage = nil
        progress = 0.0
        isConverting = false
        statusMessage = "Listo."
    }
    
    func startConversion() {
        guard let inputSourceURL = selectedFileURL else {
            errorMessage = "Selecciona un archivo antes de continuar."
            return
        }
        
        isConverting = true
        progress = 0.05
        errorMessage = nil
        statusMessage = "Preparando archivo..."
        outputFileURL = nil
        
        Task.detached(priority: .userInitiated) {
            do {
                let tempDir = FileManager.default.temporaryDirectory
                let safeBase = inputSourceURL.deletingPathExtension().lastPathComponent
                    .replacingOccurrences(of: "[^A-Za-z0-9._-]", with: "_", options: .regularExpression)
                
                let uniqueInputName = "in_\(Int(Date().timeIntervalSince1970))_\(inputSourceURL.lastPathComponent)"
                let tempInputURL = tempDir.appendingPathComponent(uniqueInputName)
                
                let isAccessing = inputSourceURL.startAccessingSecurityScopedResource()
                defer {
                    if isAccessing {
                        inputSourceURL.stopAccessingSecurityScopedResource()
                    }
                }
                
                if FileManager.default.fileExists(atPath: tempInputURL.path) {
                    try? FileManager.default.removeItem(at: tempInputURL)
                }
                
                let fileData = try Data(contentsOf: inputSourceURL)
                try fileData.write(to: tempInputURL)
                
                let format = await self.selectedFormat
                let mode = await self.selectedMode
                let quality = await self.selectedQuality
                
                let outputFileName = "\(safeBase)_\(quality.rawValue.replacingOccurrences(of: " ", with: "_")).\(format)"
                let tempOutputURL = tempDir.appendingPathComponent("out_\(Int(Date().timeIntervalSince1970))_\(outputFileName)")
                
                if FileManager.default.fileExists(atPath: tempOutputURL.path) {
                    try? FileManager.default.removeItem(at: tempOutputURL)
                }
                
                let command = await self.buildCommand(
                    inputPath: tempInputURL.path,
                    outputPath: tempOutputURL.path,
                    mode: mode,
                    format: format,
                    quality: quality
                )
                
                await MainActor.run {
                    self.statusMessage = "Convirtiendo con FFmpeg..."
                    self.progress = 0.20
                }
                
                #if canImport(ffmpegkit)
                FFmpegKit.executeAsync(command) { session in
                    guard let session = session else {
                        Task { @MainActor in
                            self.fail(message: "No se pudo iniciar la sesión de conversión.")
                        }
                        return
                    }
                    
                    let returnCode = session.getReturnCode()
                    if ReturnCode.isSuccess(returnCode) {
                        Task { @MainActor in
                            self.finishSuccess(outputURL: tempOutputURL)
                        }
                    } else {
                        let logs = session.getAllLogsAsString() ?? "Error desconocido"
                        Task { @MainActor in
                            self.fail(message: "Error al convertir (Código: \(returnCode?.description ?? "?")).")
                            print("FFmpeg Log: \(logs)")
                        }
                    }
                }
                #else
                // Fallback simulation mode if compiled without ffmpegkit framework
                try await Task.sleep(nanoseconds: 1_500_000_000)
                try fileData.write(to: tempOutputURL)
                await MainActor.run {
                    self.finishSuccess(outputURL: tempOutputURL)
                }
                #endif
                
            } catch {
                await MainActor.run {
                    self.fail(message: "Error al procesar el archivo: \(error.localizedDescription)")
                }
            }
        }
    }
    
    private func finishSuccess(outputURL: URL) {
        self.isConverting = false
        self.progress = 1.0
        self.outputFileURL = outputURL
        self.statusMessage = "¡Conversión completada con éxito!"
    }
    
    private func fail(message: String) {
        self.isConverting = false
        self.progress = 0.0
        self.errorMessage = message
        self.statusMessage = "Falló la conversión."
    }
    
    private func buildCommand(
        inputPath: String,
        outputPath: String,
        mode: MediaMode,
        format: String,
        quality: QualityLevel
    ) -> String {
        var args = ["-y", "-i", "\"\(inputPath)\""]
        
        switch mode {
        case .audio:
            args.append("-vn")
            if format == "m4a" {
                args.append(contentsOf: ["-c:a", "aac"])
            }
            if ["mp3", "m4a", "ogg", "opus", "aac"].contains(format) {
                let bitrate: String
                switch quality {
                case .highQuality: bitrate = "320k"
                case .smallFile: bitrate = "128k"
                case .balanced: bitrate = "192k"
                }
                args.append(contentsOf: ["-b:a", bitrate])
            }
            
        case .video:
            if ["mp4", "mov", "mkv"].contains(format) {
                args.append(contentsOf: ["-pix_fmt", "yuv420p"])
            }
            switch quality {
            case .smallFile:
                args.append(contentsOf: ["-vf", "scale='min(1280,iw)':-2", "-crf", "28"])
            case .balanced:
                args.append(contentsOf: ["-crf", "23"])
            case .highQuality:
                args.append(contentsOf: ["-crf", "18"])
            }
            
        case .image:
            if format == "jpg" || format == "jpeg" {
                let q: String
                switch quality {
                case .highQuality: q = "2"
                case .smallFile: q = "8"
                case .balanced: q = "4"
                }
                args.append(contentsOf: ["-q:v", q])
            } else if format == "webp" {
                let q: String
                switch quality {
                case .highQuality: q = "90"
                case .smallFile: q = "65"
                case .balanced: q = "80"
                }
                args.append(contentsOf: ["-quality", q])
            }
        }
        
        args.append("\"\(outputPath)\"")
        return args.joined(separator: " ")
    }
}
