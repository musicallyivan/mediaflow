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
            return ["m4a", "wav", "caf", "aiff", "mp3"]
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

@MainActor
class ConverterEngine: ObservableObject {
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
        
        // Detect media mode
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
        
        isConverting = true
        progress = 0.1
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
                
                let format = await self.selectedFormat.lowercased()
                let mode = await self.selectedMode
                let quality = await self.selectedQuality
                
                let outputFileName = "\(safeBase)_\(quality.rawValue.replacingOccurrences(of: " ", with: "_")).\(format)"
                let tempOutputURL = tempDir.appendingPathComponent("out_\(Int(Date().timeIntervalSince1970))_\(outputFileName)")
                
                if FileManager.default.fileExists(atPath: tempOutputURL.path) {
                    try? FileManager.default.removeItem(at: tempOutputURL)
                }
                
                await MainActor.run {
                    self.statusMessage = "Procesando con hardware acelerado de Apple..."
                    self.progress = 0.35
                }
                
                switch mode {
                case .image:
                    try self.processImage(inputURL: tempInputURL, outputURL: tempOutputURL, format: format, quality: quality)
                case .audio:
                    try await self.processAudio(inputURL: tempInputURL, outputURL: tempOutputURL, format: format, quality: quality)
                case .video:
                    try await self.processVideo(inputURL: tempInputURL, outputURL: tempOutputURL, format: format, quality: quality)
                }
                
                await MainActor.run {
                    self.finishSuccess(outputURL: tempOutputURL)
                }
                
            } catch {
                await MainActor.run {
                    self.fail(message: "Error al procesar: \(error.localizedDescription)")
                }
            }
        }
    }
    
    // MARK: - Native Processing Engines
    
    private nonisolated func processImage(inputURL: URL, outputURL: URL, format: String, quality: QualityLevel) throws {
        guard let source = CGImageSourceCreateWithURL(inputURL as CFURL, nil),
              let cgImage = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
            throw NSError(domain: "MediaFlow", code: -1, userInfo: [NSLocalizedDescriptionKey: "No se pudo leer la imagen de entrada."])
        }
        
        let utType: CFString
        switch format {
        case "png": utType = UTType.png.identifier as CFString
        case "jpg", "jpeg": utType = UTType.jpeg.identifier as CFString
        case "webp": utType = "public.webp" as CFString
        case "bmp": utType = UTType.bmp.identifier as CFString
        case "tiff": utType = UTType.tiff.identifier as CFString
        case "heic": utType = UTType.heic.identifier as CFString
        default: utType = UTType.jpeg.identifier as CFString
        }
        
        guard let destination = CGImageDestinationCreateWithURL(outputURL as CFURL, utType, 1, nil) else {
            throw NSError(domain: "MediaFlow", code: -2, userInfo: [NSLocalizedDescriptionKey: "El formato .\(format) no es compatible con el codificador del sistema."])
        }
        
        let compressionQuality: Double
        switch quality {
        case .highQuality: compressionQuality = 1.0
        case .balanced: compressionQuality = 0.8
        case .smallFile: compressionQuality = 0.5
        }
        
        let options: [CFString: Any] = [
            kCGImageDestinationLossyCompressionQuality: compressionQuality
        ]
        
        CGImageDestinationAddImage(destination, cgImage, options as CFDictionary)
        if !CGImageDestinationFinalize(destination) {
            throw NSError(domain: "MediaFlow", code: -3, userInfo: [NSLocalizedDescriptionKey: "Error al codificar la imagen."])
        }
    }
    
    private nonisolated func processVideo(inputURL: URL, outputURL: URL, format: String, quality: QualityLevel) async throws {
        let asset = AVURLAsset(url: inputURL)
        
        let presetName: String
        switch quality {
        case .highQuality: presetName = AVAssetExportPresetHighestQuality
        case .balanced: presetName = AVAssetExportPresetMediumQuality
        case .smallFile: presetName = AVAssetExportPresetLowQuality
        }
        
        guard let exportSession = AVAssetExportSession(asset: asset, presetName: presetName) else {
            throw NSError(domain: "MediaFlow", code: -4, userInfo: [NSLocalizedDescriptionKey: "No se pudo inicializar la sesión de exportación de video."])
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
        
        await exportSession.export()
        
        if exportSession.status != .completed {
            if let error = exportSession.error {
                throw error
            } else {
                throw NSError(domain: "MediaFlow", code: -5, userInfo: [NSLocalizedDescriptionKey: "Falló la exportación del video."])
            }
        }
    }
    
    private nonisolated func processAudio(inputURL: URL, outputURL: URL, format: String, quality: QualityLevel) async throws {
        let asset = AVURLAsset(url: inputURL)
        
        if format == "m4a" || format == "mp3" || format == "aac" {
            guard let exportSession = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetAppleM4A) else {
                throw NSError(domain: "MediaFlow", code: -6, userInfo: [NSLocalizedDescriptionKey: "No se pudo configurar la exportación de audio AAC/M4A."])
            }
            
            exportSession.outputURL = outputURL
            exportSession.outputFileType = .m4a
            
            await exportSession.export()
            
            if exportSession.status != .completed {
                if let error = exportSession.error {
                    throw error
                } else {
                    throw NSError(domain: "MediaFlow", code: -7, userInfo: [NSLocalizedDescriptionKey: "Falló la exportación del audio."])
                }
            }
        } else if format == "wav" || format == "aiff" || format == "caf" {
            // Uncompressed PCM audio export using AVAssetReader & AVAssetWriter
            try await self.exportUncompressedAudio(asset: asset, outputURL: outputURL, format: format)
        } else {
            // Default audio export
            guard let exportSession = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetAppleM4A) else {
                throw NSError(domain: "MediaFlow", code: -8, userInfo: [NSLocalizedDescriptionKey: "Formato de audio no compatible."])
            }
            exportSession.outputURL = outputURL
            exportSession.outputFileType = .m4a
            await exportSession.export()
        }
    }
    
    private nonisolated func exportUncompressedAudio(asset: AVAsset, outputURL: URL, format: String) async throws {
        let reader = try AVAssetReader(asset: asset)
        guard let audioTrack = try await asset.loadTracks(withMediaType: .audio).first else {
            throw NSError(domain: "MediaFlow", code: -9, userInfo: [NSLocalizedDescriptionKey: "No se encontró ninguna pista de audio en el archivo."])
        }
        
        let outputSettings: [String: Any] = [
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false,
            AVLinearPCMIsNonInterleaved: false
        ]
        
        let readerOutput = AVAssetReaderTrackOutput(track: audioTrack, outputSettings: outputSettings)
        reader.add(readerOutput)
        
        let fileType: AVFileType = (format == "aiff") ? .aiff : (format == "caf") ? .caf : .wav
        let writer = try AVAssetWriter(outputURL: outputURL, fileType: fileType)
        let writerInput = AVAssetWriterInput(mediaType: .audio, outputSettings: outputSettings)
        writer.add(writerInput)
        
        reader.startReading()
        writer.startWriting()
        writer.startSession(atSourceTime: .zero)
        
        let queue = DispatchQueue(label: "com.musicallyivan.mediaflow.audiowriter")
        
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            writerInput.requestMediaDataWhenReady(on: queue) {
                while writerInput.isReadyForMoreMediaData {
                    if let buffer = readerOutput.copyNextSampleBuffer() {
                        writerInput.append(buffer)
                    } else {
                        writerInput.markAsFinished()
                        writer.finishWriting {
                            if writer.status == .completed {
                                continuation.resume()
                            } else if let error = writer.error {
                                continuation.resume(throwing: error)
                            } else {
                                continuation.resume(throwing: NSError(domain: "MediaFlow", code: -10, userInfo: [NSLocalizedDescriptionKey: "Error al guardar el archivo de audio PCM."]))
                            }
                        }
                        break
                    }
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
}
