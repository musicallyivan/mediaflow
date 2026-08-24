import SwiftUI

struct ContentView: View {
    @StateObject private var engine = ConverterEngine()
    @State private var showingFilePicker = false
    @State private var showingShareSheet = false
    
    private let primaryTeal = Color(red: 23.0 / 255.0, green: 122.0 / 255.0, blue: 115.0 / 255.0)
    private let lightTeal = Color(red: 230.0 / 255.0, green: 242.0 / 255.0, blue: 241.0 / 255.0)
    
    var body: some View {
        NavigationView {
            ZStack {
                Color(uiColor: .systemGroupedBackground)
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: 20) {
                        headerSection
                        fileSelectionCard
                        settingsCard
                        progressAndStatusCard
                        actionButtons
                        footerNote
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    HStack(spacing: 8) {
                        Image(systemName: "waveform.circle.fill")
                            .foregroundColor(primaryTeal)
                            .font(.title3)
                        Text("Media Flow")
                            .font(.headline)
                            .fontWeight(.bold)
                    }
                }
            }
            .sheet(isPresented: $showingFilePicker) {
                DocumentPicker { url in
                    engine.selectFile(url: url)
                }
            }
            .sheet(isPresented: $showingShareSheet) {
                if let url = engine.outputFileURL {
                    ShareSheet(activityItems: [url])
                }
            }
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }
    
    // MARK: - Subviews
    
    private var headerSection: some View {
        VStack(spacing: 6) {
            Text("Convierte Audio, Video e Imagen")
                .font(.title3)
                .fontWeight(.bold)
                .foregroundColor(.primary)
            
            Text("Procesamiento local 100% privado en tu iPhone")
                .font(.footnote)
                .foregroundColor(.secondary)
        }
        .multilineTextAlignment(.center)
        .padding(.top, 4)
    }
    
    private var fileSelectionCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("Archivo a Convertir", systemImage: "doc.fill")
                .font(.system(.body, design: .default).weight(.semibold))
                // O de forma más directa en SwiftUI para iOS 15:
                .font(.body.weight(.semibold))
                .foregroundColor(primaryTeal)
            
            if engine.selectedFileURL != nil {
                HStack(spacing: 12) {
                    Image(systemName: iconForMode(engine.selectedMode))
                        .font(.title)
                        .foregroundColor(primaryTeal)
                        .frame(width: 44, height: 44)
                        .background(lightTeal)
                        .cornerRadius(10)
                    
                    VStack(alignment: .leading, spacing: 3) {
                        Text(engine.selectedFileName)
                            .font(.body)
                            .fontWeight(.medium)
                            .lineLimit(1)
                        
                        if !engine.selectedFileSize.isEmpty {
                            Text(engine.selectedFileSize)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                    
                    Button(action: { showingFilePicker = true }) {
                        Image(systemName: "pencil.circle.fill")
                            .font(.title2)
                            .foregroundColor(primaryTeal)
                    }
                }
                .padding(12)
                .background(Color(uiColor: .secondarySystemGroupedBackground))
                .cornerRadius(12)
            } else {
                Button(action: { showingFilePicker = true }) {
                    HStack {
                        Spacer()
                        VStack(spacing: 8) {
                            Image(systemName: "arrow.up.doc.fill")
                                .font(.largeTitle)
                                .foregroundColor(primaryTeal)
                            
                            Text("Seleccionar Archivo")
                                .font(.headline)
                                .foregroundColor(primaryTeal)
                            
                            Text("Audio, Video, Imagen desde Archivos o iCloud")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding(.vertical, 24)
                        Spacer()
                    }
                    .background(Color(uiColor: .secondarySystemGroupedBackground))
                    .cornerRadius(14)
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .strokeBorder(style: StrokeStyle(lineWidth: 1.5, dash: [6]))
                            .foregroundColor(primaryTeal.opacity(0.4))
                    )
                }
            }
        }
        .padding(16)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.04), radius: 6, x: 0, y: 2)
    }
    
    private var settingsCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("Ajustes de Conversión", systemImage: "slider.horizontal.3")
                .font(.system(.body, design: .default).weight(.semibold))
                // O de forma más directa en SwiftUI para iOS 15:
                .font(.body.weight(.semibold))
                .foregroundColor(primaryTeal)
            
            // Mode selector
            VStack(alignment: .leading, spacing: 6) {
                Text("Tipo de Medio")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Picker("Tipo", selection: $engine.selectedMode) {
                    ForEach(MediaMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
            }
            
            // Format selector
            VStack(alignment: .leading, spacing: 6) {
                Text("Formato de Salida")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(engine.selectedMode.defaultFormats, id: \.self) { format in
                            Button(action: { engine.selectedFormat = format }) {
                                Text(format.uppercased())
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 8)
                                    .background(engine.selectedFormat == format ? primaryTeal : Color(uiColor: .tertiarySystemGroupedBackground))
                                    .foregroundColor(engine.selectedFormat == format ? .white : .primary)
                                    .cornerRadius(8)
                            }
                        }
                    }
                }
            }
            
            // Quality selector
            VStack(alignment: .leading, spacing: 6) {
                Text("Calidad")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Picker("Calidad", selection: $engine.selectedQuality) {
                    ForEach(QualityLevel.allCases) { q in
                        Text(q.rawValue).tag(q)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
            }
        }
        .padding(16)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.04), radius: 6, x: 0, y: 2)
    }
    
    private var progressAndStatusCard: some View {
        VStack(spacing: 12) {
            if engine.isConverting {
                ProgressView(value: engine.progress, total: 1.0)
                    .progressViewStyle(LinearProgressViewStyle(tint: primaryTeal))
                    .padding(.top, 4)
            }
            
            HStack {
                if engine.isConverting {
                    ProgressView()
                        .scaleEffect(0.8)
                        .padding(.trailing, 4)
                } else if engine.outputFileURL != nil {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                } else if engine.errorMessage != nil {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.red)
                }
                
                Text(engine.errorMessage ?? engine.statusMessage)
                    .font(.subheadline)
                    .foregroundColor(engine.errorMessage != nil ? .red : .secondary)
                    .lineLimit(2)
                
                Spacer()
            }
        }
        .padding(14)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .cornerRadius(14)
        .shadow(color: Color.black.opacity(0.03), radius: 4, x: 0, y: 1)
    }
    
    private var actionButtons: some View {
        VStack(spacing: 10) {
            if engine.outputFileURL != nil {
                Button(action: { showingShareSheet = true }) {
                    HStack {
                        Image(systemName: "square.and.arrow.up.fill")
                        Text("Guardar / Compartir Archivo")
                            .fontWeight(.bold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(primaryTeal)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                
                Button(action: { engine.reset() }) {
                    HStack {
                        Image(systemName: "arrow.counterclockwise")
                        Text("Convertir Otro Archivo")
                            .fontWeight(.medium)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(Color(uiColor: .secondarySystemGroupedBackground))
                    .foregroundColor(primaryTeal)
                    .cornerRadius(12)
                }
            } else {
                Button(action: { engine.startConversion() }) {
                    HStack {
                        Image(systemName: "bolt.fill")
                        Text(engine.isConverting ? "Convirtiendo..." : "Convertir Ahora")
                            .fontWeight(.bold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(engine.selectedFileURL != nil && !engine.isConverting ? primaryTeal : Color.gray.opacity(0.4))
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .disabled(engine.selectedFileURL == nil || engine.isConverting)
            }
        }
    }
    
    private var footerNote: some View {
        Text("Media Flow procesa los archivos 100% en tu dispositivo utilizando hardware acelerado de Apple.")
            .font(.caption2)
            .foregroundColor(.secondary)
            .multilineTextAlignment(.center)
            .padding(.horizontal, 10)
            .padding(.top, 6)
    }
    
    private func iconForMode(_ mode: MediaMode) -> String {
        switch mode {
        case .audio: return "music.note"
        case .video: return "film"
        case .image: return "photo"
        }
    }
}
