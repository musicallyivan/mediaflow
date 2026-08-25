import SwiftUI

struct ContentView: View {
    @StateObject private var engine = ConverterEngine()
    @State private var showingFilePicker = false
    @State private var showingShareSheet = false
    @State private var showingSettings = false
    @State private var showingInfo = false
    
    private let primaryTeal = Color(red: 23.0 / 255.0, green: 122.0 / 255.0, blue: 115.0 / 255.0)
    
    var body: some View {
        NavigationStack {
            ZStack {
                background
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 18) {
                        hero
                        fileCard
                        conversionCard
                        statusCard
                        actionArea
                        privacyNote
                    }
                    .padding(.horizontal, 18)
                    .padding(.top, 10)
                    .padding(.bottom, 28)
                }
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    HStack(spacing: 9) {
                        Image(systemName: "waveform.circle.fill")
                            .font(.title3)
                            .foregroundStyle(primaryTeal)
                        Text("Media Flow")
                            .font(.headline.weight(.bold))
                    }
                }
                
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Button { showingInfo = true } label: {
                        Image(systemName: "info.circle")
                    }
                    .accessibilityLabel("Información")
                    
                    Button { showingSettings = true } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Ajustes")
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
            .sheet(isPresented: $showingSettings) {
                SettingsView()
            }
            .sheet(isPresented: $showingInfo) {
                InfoView()
            }
        }
        .tint(primaryTeal)
    }
    
    private var background: some View {
        ZStack {
            Color(uiColor: .systemGroupedBackground)
                .ignoresSafeArea()
            
            Circle()
                .fill(primaryTeal.opacity(0.10))
                .frame(width: 260, height: 260)
                .blur(radius: 45)
                .offset(x: 150, y: -300)
            
            Circle()
                .fill(Color.blue.opacity(0.07))
                .frame(width: 220, height: 220)
                .blur(radius: 50)
                .offset(x: -160, y: 350)
        }
    }
    
    private var hero: some View {
        VStack(spacing: 10) {
            ZStack {
                Circle()
                    .fill(primaryTeal.opacity(0.13))
                    .frame(width: 76, height: 76)
                
                Image(systemName: "waveform.and.mic")
                    .font(.system(size: 32, weight: .semibold))
                    .foregroundStyle(primaryTeal)
            }
            
            Text("Convierte tus archivos")
                .font(.system(size: 29, weight: .bold, design: .rounded))
                .multilineTextAlignment(.center)
            
            Text("Audio, vídeo e imagen. Todo se procesa en tu iPhone, sin subir tus archivos.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 16)
        }
        .padding(.top, 6)
        .padding(.bottom, 4)
    }
    
    private var fileCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("Archivo", systemImage: "doc.fill")
            
            if engine.selectedFileURL != nil {
                HStack(spacing: 13) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 15, style: .continuous)
                            .fill(primaryTeal.opacity(0.13))
                        Image(systemName: iconForMode(engine.selectedMode))
                            .font(.title2.weight(.semibold))
                            .foregroundStyle(primaryTeal)
                    }
                    .frame(width: 54, height: 54)
                    
                    VStack(alignment: .leading, spacing: 4) {
                        Text(engine.selectedFileName)
                            .font(.subheadline.weight(.semibold))
                            .lineLimit(1)
                        
                        if !engine.selectedFileSize.isEmpty {
                            Text(engine.selectedFileSize)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    
                    Spacer(minLength: 6)
                    
                    Button {
                        showingFilePicker = true
                        haptic()
                    } label: {
                        Image(systemName: "arrow.triangle.2.circlepath")
                            .font(.headline.weight(.semibold))
                            .frame(width: 38, height: 38)
                    }
                    .buttonStyle(.borderless)
                    .accessibilityLabel("Cambiar archivo")
                }
                .padding(12)
                .liquidGlass(cornerRadius: 18)
            } else {
                Button {
                    showingFilePicker = true
                    haptic()
                } label: {
                    VStack(spacing: 11) {
                        Image(systemName: "arrow.up.doc")
                            .font(.system(size: 30, weight: .medium))
                            .foregroundStyle(primaryTeal)
                        
                        Text("Seleccionar archivo")
                            .font(.headline.weight(.semibold))
                        
                        Text("Archivos, iCloud Drive y otras ubicaciones")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 25)
                }
                .buttonStyle(.plain)
                .liquidGlass(cornerRadius: 22)
            }
        }
        .padding(18)
        .liquidGlass(cornerRadius: 26)
    }
    
    private var conversionCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            sectionTitle("Conversión", systemImage: "slider.horizontal.3")
            
            VStack(alignment: .leading, spacing: 8) {
                Text("Tipo de medio")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.secondary)
                
                Picker("Tipo de medio", selection: $engine.selectedMode) {
                    ForEach(MediaMode.allCases) { mode in
                        Label(mode.rawValue, systemImage: iconForMode(mode))
                            .tag(mode)
                    }
                }
                .pickerStyle(.segmented)
            }
            
            VStack(alignment: .leading, spacing: 8) {
                Text("Formato de salida")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.secondary)
                
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(engine.selectedMode.defaultFormats, id: \.self) { format in
                            Button {
                                engine.selectedFormat = format
                                haptic()
                            } label: {
                                Text(format.uppercased())
                                    .font(.caption.weight(.bold))
                                    .padding(.horizontal, 15)
                                    .padding(.vertical, 10)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(engine.selectedFormat == format ? .white : .primary)
                            .background {
                                Capsule()
                                    .fill(engine.selectedFormat == format ? primaryTeal : Color(uiColor: .tertiarySystemGroupedBackground))
                            }
                        }
                    }
                }
            }
            
            VStack(alignment: .leading, spacing: 8) {
                Text("Calidad")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.secondary)
                
                Picker("Calidad", selection: $engine.selectedQuality) {
                    ForEach(QualityLevel.allCases) { quality in
                        Text(quality.rawValue).tag(quality)
                    }
                }
                .pickerStyle(.segmented)
            }
        }
        .padding(18)
        .liquidGlass(cornerRadius: 26)
    }
    
    private var statusCard: some View {
        Group {
            if engine.isConverting || engine.outputFileURL != nil || engine.errorMessage != nil {
                VStack(spacing: 13) {
                    HStack(spacing: 12) {
                        statusIcon
                        
                        VStack(alignment: .leading, spacing: 3) {
                            Text(statusTitle)
                                .font(.subheadline.weight(.semibold))
                            Text(engine.errorMessage ?? engine.statusMessage)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(2)
                        }
                        
                        Spacer()
                        
                        if engine.isConverting {
                            Text("\(Int(engine.progress * 100))%")
                                .font(.caption.weight(.bold))
                                .monospacedDigit()
                                .foregroundStyle(primaryTeal)
                        }
                    }
                    
                    if engine.isConverting {
                        ProgressView(value: engine.progress)
                            .tint(primaryTeal)
                            .animation(.easeInOut, value: engine.progress)
                    }
                }
                .padding(17)
                .liquidGlass(cornerRadius: 24)
            }
        }
    }
    
    private var actionArea: some View {
        VStack(spacing: 10) {
            if engine.outputFileURL != nil {
                Button {
                    showingShareSheet = true
                    haptic()
                } label: {
                    Label("Guardar y compartir", systemImage: "square.and.arrow.up")
                        .font(.headline.weight(.bold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 15)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.white)
                .background {
                    RoundedRectangle(cornerRadius: 19, style: .continuous)
                        .fill(primaryTeal)
                }
                
                Button {
                    engine.reset()
                    haptic()
                } label: {
                    Label("Convertir otro archivo", systemImage: "arrow.counterclockwise")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 13)
                }
                .buttonStyle(.plain)
                .foregroundStyle(primaryTeal)
                .liquidGlass(cornerRadius: 19)
            } else {
                Button {
                    engine.startConversion()
                    haptic()
                } label: {
                    HStack(spacing: 9) {
                        Image(systemName: engine.isConverting ? "hourglass" : "bolt.fill")
                        Text(engine.isConverting ? "Convirtiendo…" : "Convertir ahora")
                            .fontWeight(.bold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.white)
                .background {
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .fill(engine.selectedFileURL != nil && !engine.isConverting ? primaryTeal : Color.gray.opacity(0.35))
                }
                .disabled(engine.selectedFileURL == nil || engine.isConverting)
                .animation(.easeInOut(duration: 0.2), value: engine.selectedFileURL != nil)
            }
        }
    }
    
    private var privacyNote: some View {
        Label("Procesamiento local y privado", systemImage: "lock.shield.fill")
            .font(.caption)
            .foregroundStyle(.secondary)
            .padding(.top, 2)
    }
    
    private var statusIcon: some View {
        ZStack {
            Circle()
                .fill(statusColor.opacity(0.13))
                .frame(width: 42, height: 42)
            
            if engine.isConverting {
                ProgressView()
                    .tint(statusColor)
            } else {
                Image(systemName: engine.errorMessage != nil ? "exclamationmark.triangle.fill" : "checkmark")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(statusColor)
            }
        }
    }
    
    private var statusTitle: String {
        if engine.isConverting { return "Convirtiendo" }
        if engine.errorMessage != nil { return "Ha ocurrido un error" }
        return "Conversión completada"
    }
    
    private var statusColor: Color {
        if engine.errorMessage != nil { return .red }
        if engine.isConverting { return primaryTeal }
        return .green
    }
    
    private func sectionTitle(_ title: String, systemImage: String) -> some View {
        Label(title, systemImage: systemImage)
            .font(.headline.weight(.bold))
            .foregroundStyle(primaryTeal)
    }
    
    private func iconForMode(_ mode: MediaMode) -> String {
        switch mode {
        case .audio: return "music.note"
        case .video: return "film"
        case .image: return "photo"
        }
    }
    
    private func haptic() {
        #if os(iOS)
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
        #endif
    }
}

private extension View {
    @ViewBuilder
    func liquidGlass(cornerRadius: CGFloat) -> some View {
        if #available(iOS 26.0, *) {
            self.glassEffect(.regular, in: .rect(cornerRadius: cornerRadius))
        } else {
            self
                .background(Color(uiColor: .secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .stroke(Color.primary.opacity(0.06), lineWidth: 0.8)
                }
        }
    }
}

private struct SettingsView: View {
    var body: some View {
        NavigationStack {
            List {
                Section("Media Flow") {
                    LabeledContent("Versión", value: "1.7.1")
                    LabeledContent("Procesamiento", value: "En el dispositivo")
                }
                
                Section("Privacidad") {
                    Label("Tus archivos no se suben a ningún servidor.", systemImage: "lock.shield")
                    Label("La conversión se realiza localmente.", systemImage: "iphone")
                }
            }
            .navigationTitle("Ajustes")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
    }
}

private struct InfoView: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 18) {
                Image(systemName: "waveform.circle.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(Color(red: 23.0 / 255.0, green: 122.0 / 255.0, blue: 115.0 / 255.0))
                
                Text("Media Flow")
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                
                Text("Conversor multimedia rápido, privado y diseñado para iPhone.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 28)
                
                Spacer()
            }
            .padding(.top, 35)
            .navigationTitle("Información")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Cerrar") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium])
    }
}
