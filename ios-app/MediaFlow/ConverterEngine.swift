import Foundation
import Combine
import AVFoundation
import ImageIO
import CoreGraphics
import UniformTypeIdentifiers

enum MediaMode: String, CaseIterable, Identifiable {
    case audio = "Audio"
    case video = "Video"
    case image = "Imagen"
    
    var id: String { rawValue }
    
    var defaultFormats: [String] {
        switch self {
        case .audio:
            return ["m4a", "aac", "mp3", "wav", "caf"]
        case .video:
            return ["mp4", "mov", "m4v"]
        case .image:
            return ["jpg", "png", "heic", "webp", "tiff", "bmp"]
        }
    }
}

enum QualityLevel: String, CaseIterable, Identifiable {
    case balanced = "Equilibrada"
    case smallFile = "Archivo pequeño"
    case highQuality = "Alta calidad"
    
    var id: String { rawValue }
}

final class ConverterEngine: ObservableObject {
    @Published var selectedMode: MediaMode = .audio {
        didSet {
            if !selectedMode.defaultFormats.contains(selectedFormat) {
                selectedFormat = selectedMode.defaultFormats.first ?? "m4a"
            }
        }
    }
    @Published var selectedFormat: String = "m4a"
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
    
    func selectFile(url: URL) {
        let isSecurityScoped = url.startAccessingSecurityScopedResource()
        defer {
            if isSecurityScoped {
                url.stopAccessingSecurityScopedResource()
            }
        }
        
        let tempDir = FileManager.default.temporaryDirectory
        let safeName = "selected_\(Int(Date().timeIntervalSince1970))_\(url.lastPathComponent)"
        let localTempURL = tempDir.appendingPathComponent(safeName)
        
        if FileManager.default.fileExists(atPath: localTempURL.path) {
            try? FileManager.default.removeItem(at: localTempURL)
        }
        
        do {
            try FileManager.default.copyItem(at: url, to: localTempURL)
            selectedFileURL = localTempURL
        } catch {
            selectedFileURL = url
        }
        
        selectedFileName = url.lastPathComponent
        
        let inspectionPath = selectedFileURL?.path ?? url.path
        if let attributes = try? FileManager.default.attributesOfItem(atPath: inspectionPath),
           let size = attributes[.size] as? Int64 {
            selectedFileSize = ByteCountFormatter.string(fromByteCount: size, countStyle: .file)
        } else {
            selectedFileSize = ""
        }
        
        outputFileURL = nil
        errorMessage = nil
        progress = 0.0
        statusMessage = "Archivo cargado: \(selectedFileName)"
        
        let ext = url.pathExtension.lowercased()
        if ["mp3", "wav", "m4a", "flac", "ogg", "aac", "aiff", "caf"].contains(ext) {
            selectedMode = .audio
        } else if ["mp4", "mov", "webm", "mkv", "avi", "m4v", "3gp"].contains(ext) {
            selectedMode = .video
        } else if ["png", "jpg", "jpeg", "webp", "bmp", "heic", "tiff"].contains(ext) {
            selectedMode = .image
        }
        selectedFormat = selectedMode.defaultFormats.first ?? "m4a"
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
        
        let targetFormat = selectedFormat.lowercased()
        let targetMode = selectedMode
        let targetQuality = selectedQuality
        let fileName = selectedFileName
        
        isConverting = true
        progress = 0.15
        errorMessage = nil
        statusMessage = "Preparando archivo..."
        outputFileURL = nil
        
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            do {
                let tempDir = FileManager.default.temporaryDirectory
                let safeBase = inputSourceURL.deletingPathExtension().lastPathComponent
                    .replacingOccurrences(of: "[^A-Za-z0-9._-]", with: "_", options: .regularExpression)
                
                let uniqueInputName = "in_\(Int(Date().timeIntervalSince1970))_\(fileName)"
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
                
                if inputSourceURL.path != tempInputURL.path {
                    if FileManager.default.fileExists(atPath: inputSourceURL.path) {
                        try? FileManager.default.copyItem(at: inputSourceURL, to: tempInputURL)
                    } else {
                        let fileData = try Data(contentsOf: inputSourceURL)
                        try fileData.write(to: tempInputURL)
                    }
                }
                
                let qualitySuffix = targetQuality.rawValue.replacingOccurrences(of: " ", with: "_")
                let outputFileName = "\(safeBase)_\(qualitySuffix).\(targetFormat)"
                let tempOutputURL = tempDir.appendingPathComponent("out_\(Int(Date().timeIntervalSince1970))_\(outputFileName)")
                
                if FileManager.default.fileExists(atPath: tempOutputURL.path) {
                    try? FileManager.default.removeItem(at: tempOutputURL)
                }
                
                DispatchQueue.main.async {
                    self?.statusMessage = "Procesando con hardware de Apple..."
                    self?.progress = 0.40
                }
                
                switch targetMode {
                case .image:
                    try ConverterEngine.processImage(inputURL: tempInputURL, outputURL: tempOutputURL, format: targetFormat, quality: targetQuality)
                    DispatchQueue.main.async {
                        self?.finishSuccess(outputURL: tempOutputURL)
                    }
                case .video:
                    ConverterEngine.processVideo(inputURL: tempInputURL, outputURL: tempOutputURL, format: targetFormat, quality: targetQuality) { result in
                        DispatchQueue.main.async {
                            switch result {
                            case .success(let url):
                                self?.finishSuccess(outputURL: url)
                            case .failure(let error):
                                self?.fail(message: error.localizedDescription)
                            }
                        }
                    }
                case .audio:
                    ConverterEngine.processAudio(inputURL: tempInputURL, outputURL: tempOutputURL, format: targetFormat, quality: targetQuality) { result in
                        DispatchQueue.main.async {
                            switch result {
                            case .success(let url):
                                self?.finishSuccess(outputURL: url)
                            case .failure(let error):
                                self?.fail(message: error.localizedDescription)
                            }
                        }
                    }
                }
                
            } catch {
                DispatchQueue.main.async {
                    self?.fail(message: "Error: \(error.localizedDescription)")
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
    
    // MARK: - Static Processing Helpers
    
    private static func processImage(inputURL: URL, outputURL: URL, format: String, quality: QualityLevel) throws {
        guard let source = CGImageSourceCreateWithURL(inputURL as CFURL, nil),
              let cgImage = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
            throw NSError(domain: "MediaFlow", code: -1, userInfo: [NSLocalizedDescriptionKey: "No se pudo leer la imagen seleccionada."])
        }
        
        let typeIdentifier: CFString
        switch format {
        case "png":
            typeIdentifier = UTType.png.identifier as CFString
        case "jpg", "jpeg":
            typeIdentifier = UTType.jpeg.identifier as CFString
        case "webp":
            typeIdentifier = "public.webp" as CFString
        case "bmp":
            typeIdentifier = UTType.bmp.identifier as CFString
        case "tiff":
            typeIdentifier = UTType.tiff.identifier as CFString
        case "heic":
            typeIdentifier = UTType.heic.identifier as CFString
        default:
            typeIdentifier = UTType.jpeg.identifier as CFString
        }
        
        guard let destination = CGImageDestinationCreateWithURL(outputURL as CFURL, typeIdentifier, 1, nil) else {
            throw NSError(domain: "MediaFlow", code: -2, userInfo: [NSLocalizedDescriptionKey: "Formato no compatible con este dispositivo."])
        }
        
        let compression: Float
        switch quality {
        case .highQuality: compression = 1.0
        case .balanced: compression = 0.8
        case .smallFile: compression = 0.5
        }
        
        let options: [CFString: Any] = [
            kCGImageDestinationLossyCompressionQuality: NSNumber(value: compression)
        ]
        CGImageDestinationAddImage(destination, cgImage, options as CFDictionary)
        
        if !CGImageDestinationFinalize(destination) {
            throw NSError(domain: "MediaFlow", code: -3, userInfo: [NSLocalizedDescriptionKey: "Error al guardar la imagen procesada."])
        }
    }
    
    private static func processVideo(inputURL: URL, outputURL: URL, format: String, quality: QualityLevel, completion: @escaping (Result<URL, Error>) -> Void) {
        let asset = AVURLAsset(url: inputURL)
        
        let preset: String
        switch quality {
        case .highQuality: preset = AVAssetExportPresetHighestQuality
        case .balanced: preset = AVAssetExportPresetMediumQuality
        case .smallFile: preset = AVAssetExportPresetLowQuality
        }
        
        guard let exportSession = AVAssetExportSession(asset: asset, presetName: preset) else {
            completion(.failure(NSError(domain: "MediaFlow", code: -4, userInfo: [NSLocalizedDescriptionKey: "No se pudo crear la sesión de exportación de video."])))
            return
        }
        
        let fileType: AVFileType
        switch format {
        case "mov": fileType = .mov
        case "m4v": fileType = .m4v
        default: fileType = .mp4
        }
        
        exportSession.outputURL = outputURL
        exportSession.outputFileType = fileType
        exportSession.shouldOptimizeForNetworkUse = true
        
        exportSession.exportAsynchronously {
            switch exportSession.status {
            case .completed:
                completion(.success(outputURL))
            case .failed:
                completion(.failure(exportSession.error ?? NSError(domain: "MediaFlow", code: -5, userInfo: [NSLocalizedDescriptionKey: "Falló la exportación del video."])))
            case .cancelled:
                completion(.failure(NSError(domain: "MediaFlow", code: -6, userInfo: [NSLocalizedDescriptionKey: "Exportación cancelada."])))
            default:
                completion(.failure(NSError(domain: "MediaFlow", code: -7, userInfo: [NSLocalizedDescriptionKey: "Estado de exportación desconocido."])))
            }
        }
    }
    
    private static func processAudio(inputURL: URL, outputURL: URL, format: String, quality: QualityLevel, completion: @escaping (Result<URL, Error>) -> Void) {
        let asset = AVURLAsset(url: inputURL)
        
        guard let exportSession = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetAppleM4A) else {
            completion(.failure(NSError(domain: "MediaFlow", code: -8, userInfo: [NSLocalizedDescriptionKey: "No se pudo configurar la exportación de audio."])))
            return
        }
        
        exportSession.outputURL = outputURL
        exportSession.outputFileType = .m4a
        
        exportSession.exportAsynchronously {
            switch exportSession.status {
            case .completed:
                completion(.success(outputURL))
            case .failed:
                completion(.failure(exportSession.error ?? NSError(domain: "MediaFlow", code: -9, userInfo: [NSLocalizedDescriptionKey: "Falló la conversión de audio."])))
            case .cancelled:
                completion(.failure(NSError(domain: "MediaFlow", code: -10, userInfo: [NSLocalizedDescriptionKey: "Conversión de audio cancelada."])))
            default:
                completion(.failure(NSError(domain: "MediaFlow", code: -11, userInfo: [NSLocalizedDescriptionKey: "Estado desconocido en audio."])))
            }
        }
    }
}
