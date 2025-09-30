// Elementos DOM
const searchForm = document.getElementById('searchForm');
const placaInput = document.getElementById('placa');
const thresholdSlider = document.getElementById('threshold');
const thresholdValue = document.getElementById('thresholdValue');
const loadingDiv = document.getElementById('loading');
const resultsDiv = document.getElementById('results');
const errorDiv = document.getElementById('error');
const errorText = document.getElementById('errorText');
const summaryDiv = document.getElementById('summary');
const variationsDiv = document.getElementById('variationsInfo');
const detectionsDiv = document.getElementById('detections');
const apiStatusSpan = document.getElementById('apiStatus');
const imageModal = document.getElementById('imageModal');
const modalImage = document.getElementById('modalImage');
const modalInfo = document.getElementById('modalInfo');

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Configura eventos
    setupEventListeners();
    
    // Verifica status da API
    checkApiStatus();
    
    // Configura slider de threshold
    updateThresholdDisplay();
}

function setupEventListeners() {
    // Formulário de busca
    searchForm.addEventListener('submit', handleSearch);
    
    // Slider de threshold
    thresholdSlider.addEventListener('input', updateThresholdDisplay);
    
    // Input de placa - formatação automática
    placaInput.addEventListener('input', formatPlacaInput);
    
    // Modal
    window.addEventListener('click', function(event) {
        if (event.target === imageModal) {
            closeModal();
        }
    });
    
    // Tecla ESC para fechar modal
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
}

function updateThresholdDisplay() {
    const value = parseFloat(thresholdSlider.value);
    thresholdValue.textContent = Math.round(value * 100) + '%';
}

function formatPlacaInput(event) {
    let value = event.target.value.toUpperCase();
    // Remove caracteres especiais exceto letras e números
    value = value.replace(/[^A-Z0-9]/g, '');
    // Limita a 7 caracteres
    if (value.length > 7) {
        value = value.substring(0, 7);
    }
    event.target.value = value;
}

async function checkApiStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (response.ok) {
            apiStatusSpan.innerHTML = '<i class="fas fa-circle status-online"></i> API Online';
            apiStatusSpan.className = 'status-online';
            
            if (!data.video_existe) {
                showError('⚠️ Vídeo não encontrado! Verifique se o arquivo "teste.mp4" existe.');
            }
        } else {
            throw new Error('API offline');
        }
    } catch (error) {
        apiStatusSpan.innerHTML = '<i class="fas fa-circle status-offline"></i> API Offline';
        apiStatusSpan.className = 'status-offline';
        showError('Erro de conexão com a API. Verifique se o servidor está rodando.');
    }
}

async function handleSearch(event) {
    event.preventDefault();
    
    const placa = placaInput.value.trim();
    const threshold = parseFloat(thresholdSlider.value);
    
    if (!placa) {
        showError('Por favor, digite uma placa.');
        return;
    }
    
    if (placa.length < 6) {
        showError('A placa deve ter pelo menos 6 caracteres.');
        return;
    }
    
    // Limpa resultados anteriores
    hideAll();
    showLoading();
    
    try {
        console.log(`🔍 Iniciando busca: ${placa} (threshold: ${threshold})`);
        
        const response = await fetch('/api/buscar-placa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                placa: placa,
                threshold: threshold
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (response.ok) {
            if (data.sucesso) {
                displayResults(data);
                console.log(`✅ Busca concluída: ${data.total_deteccoes} detecções encontradas`);
            } else {
                displayNoResults(data);
                console.log('❌ Nenhuma detecção encontrada');
            }
        } else {
            throw new Error(data.erro || 'Erro na busca');
        }
        
    } catch (error) {
        hideLoading();
        console.error('❌ Erro na busca:', error);
        showError(`Erro na busca: ${error.message}`);
    }
}

function displayResults(data) {
    // Atualiza sumário
    summaryDiv.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <strong>${data.total_deteccoes}</strong> detecção(ões) encontrada(s) para a placa <strong>${data.placa_pesquisada}</strong>
    `;
    
    // Exibe variações buscadas
    displayVariations(data.variacoes_buscadas);
    
    // Exibe detecções
    displayDetections(data.deteccoes);
    
    // Mostra seção de resultados
    resultsDiv.classList.remove('hidden');
}

function displayNoResults(data) {
    summaryDiv.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        Nenhuma detecção encontrada para a placa <strong>${data.placa_pesquisada}</strong>
    `;
    
    displayVariations(data.variacoes_buscadas);
    
    detectionsDiv.innerHTML = `
        <div class="no-results">
            <i class="fas fa-search" style="font-size: 3rem; color: #ccc; margin-bottom: 20px;"></i>
            <h3 style="color: #666; margin-bottom: 15px;">Nenhuma placa encontrada</h3>
            <p style="color: #888;">
                Tente ajustar a precisão da busca ou verifique se a placa está correta.
                <br>O sistema buscou por todas as variações possíveis da placa informada.
            </p>
        </div>
    `;
    
    resultsDiv.classList.remove('hidden');
}

function displayVariations(variacoes) {
    variationsDiv.innerHTML = `
        <h3><i class="fas fa-list"></i> Variações Buscadas</h3>
        <p>O sistema buscou por estas variações da placa para compensar possíveis erros de OCR:</p>
        <div class="variations-list">
            ${variacoes.map(variacao => `<span class="variation-tag">${variacao}</span>`).join('')}
        </div>
    `;
}

function displayDetections(deteccoes) {
    if (deteccoes.length === 0) {
        return;
    }
    
    const detectionsHTML = deteccoes.map((deteccao, index) => `
        <div class="detection-card">
            <div class="detection-header">
                <span class="detection-title">Detecção ${index + 1} - Frame ${deteccao.frame}</span>
                <span class="similarity-badge">${Math.round(deteccao.similaridade * 100)}% de certeza</span>
            </div>
            
            <div class="detection-images">
                <div class="image-container" onclick="openModal('${deteccao.frame_base64}', 'Frame Completo', ${JSON.stringify(deteccao).replace(/"/g, '&quot;')})">
                    <img src="data:image/jpeg;base64,${deteccao.frame_base64}" alt="Frame ${deteccao.frame}">
                    <div class="image-label">Frame Completo</div>
                </div>
                <div class="image-container" onclick="openModal('${deteccao.moto_base64}', 'Moto Detectada', ${JSON.stringify(deteccao).replace(/"/g, '&quot;')})">
                    <img src="data:image/jpeg;base64,${deteccao.moto_base64}" alt="Moto Frame ${deteccao.frame}">
                    <div class="image-label">Moto Detectada</div>
                </div>
            </div>
            
            <div class="detection-info">
                <div class="info-row">
                    <span class="info-label">Texto OCR:</span>
                    <span class="info-value">${deteccao.texto_ocr}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Texto Limpo:</span>
                    <span class="info-value">${deteccao.texto_limpo}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Similaridade:</span>
                    <span class="info-value">${Math.round(deteccao.similaridade * 100)}%</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Confiança OCR:</span>
                    <span class="info-value">${Math.round(deteccao.confianca * 100)}%</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Timestamp:</span>
                    <span class="info-value">${deteccao.timestamp}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    detectionsDiv.innerHTML = detectionsHTML;
}

function openModal(base64Image, title, detectionData) {
    const detection = typeof detectionData === 'string' ? JSON.parse(detectionData) : detectionData;
    
    modalImage.src = `data:image/jpeg;base64,${base64Image}`;
    modalImage.alt = title;
    
    modalInfo.innerHTML = `
        <h3>${title}</h3>
        <div class="modal-details">
            <p><strong>Frame:</strong> ${detection.frame}</p>
            <p><strong>Texto OCR:</strong> ${detection.texto_ocr}</p>
            <p><strong>Texto Limpo:</strong> ${detection.texto_limpo}</p>
            <p><strong>Similaridade:</strong> ${Math.round(detection.similaridade * 100)}%</p>
            <p><strong>Confiança OCR:</strong> ${Math.round(detection.confianca * 100)}%</p>
        </div>
    `;
    
    imageModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    imageModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
}

function showLoading() {
    loadingDiv.classList.remove('hidden');
    
    // Desabilita botão de busca
    const submitBtn = searchForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buscando...';
}

function hideLoading() {
    loadingDiv.classList.add('hidden');
    
    // Reabilita botão de busca
    const submitBtn = searchForm.querySelector('button[type="submit"]');
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-search"></i> Buscar Placa';
}

function showError(message) {
    errorText.textContent = message;
    errorDiv.classList.remove('hidden');
    
    // Auto-hide após 8 segundos
    setTimeout(() => {
        errorDiv.classList.add('hidden');
    }, 8000);
}

function hideAll() {
    resultsDiv.classList.add('hidden');
    errorDiv.classList.add('hidden');
}

// Funções utilitárias
function formatDateTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('pt-BR');
}

function formatPlaca(placa) {
    if (placa.length === 7) {
        return `${placa.substring(0, 3)}-${placa.substring(3)}`;
    }
    return placa;
}

// Logs para debug
console.log('🚀 MottuGrid Placa Detector - Interface carregada');
console.log('📱 Para debug, abra o DevTools e monitore este console');