INDEX_HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HPD OCR Studio - PaddleOCR-VL 1.6</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
  <style>
    body { font-family: 'Inter', sans-serif; }
    .dropzone { border: 2px dashed #cbd5e1; transition: all 0.2s ease; }
    .dropzone.dragover { border-color: #3b82f6; background-color: #eff6ff; }
    pre { white-space: pre-wrap; word-break: break-word; }
    .hidden { display: none !important; }
    .btn-ocr-action {
      background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
      color: white !important;
      font-weight: 600;
      transition: all 0.2s ease;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
    }
    .btn-ocr-action:hover {
      background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.4);
      transform: translateY(-1px);
    }
    .btn-ocr-ready {
      background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
      box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35) !important;
    }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col">
  <!-- Header -->
  <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-xl shadow">
          VL
        </div>
        <div>
          <h1 class="text-lg font-bold leading-tight">HPD OCR Studio</h1>
          <p class="text-xs text-slate-500">PaddleOCR-VL-1.6 (0.9B VLM) · GPU Acceleration</p>
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2 text-xs bg-slate-100 py-1.5 px-3 rounded-full text-slate-600">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span id="backend-status">Đang kiểm tra kết nối...</span>
        </div>
        <a href="/docs" target="_blank" class="text-xs text-blue-600 hover:text-blue-800 font-medium">API Docs ↗</a>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full flex flex-col gap-6">
    <!-- Controls & Drag-Drop -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left Column: Upload & Options (5 cols) -->
      <div class="lg:col-span-5 flex flex-col gap-4">
        <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex flex-col gap-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h2 class="font-semibold text-slate-800">Tải tệp tài liệu</h2>
            <div class="flex flex-wrap items-center gap-1.5">
              <button id="btn-sample-pdf" type="button" class="text-[11px] text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 font-medium px-2 py-1 rounded transition border border-red-200 flex items-center gap-1">
                <span>📑</span> Mẫu PDF
              </button>
              <button id="btn-sample-jpg" type="button" class="text-[11px] text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 font-medium px-2 py-1 rounded transition border border-blue-200 flex items-center gap-1">
                <span>🖼️</span> Mẫu JPG
              </button>
              <button id="btn-sample" type="button" class="text-[11px] text-slate-600 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 font-medium px-2 py-1 rounded transition border border-slate-200">
                Mẫu PNG
              </button>
            </div>
          </div>

          <!-- Format Tabs -->
          <div class="flex items-center gap-1 p-1 bg-slate-100 rounded-xl text-xs">
            <button id="tab-mode-all" type="button" class="flex-1 py-1.5 px-2 font-semibold rounded-lg bg-white text-slate-800 shadow-sm transition">
              Tất cả
            </button>
            <button id="tab-mode-pdf" type="button" class="flex-1 py-1.5 px-2 font-medium rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1">
              <span class="w-2 h-2 rounded-full bg-red-500"></span>
              Tài liệu PDF
            </button>
            <button id="tab-mode-jpg" type="button" class="flex-1 py-1.5 px-2 font-medium rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1">
              <span class="w-2 h-2 rounded-full bg-blue-500"></span>
              Ảnh JPG/PNG
            </button>
          </div>

          <!-- Drop Area -->
          <div id="dropzone" class="dropzone rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-50 relative min-h-[200px]">
            <input type="file" id="file-input" class="hidden" accept=".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf">
            
            <div id="dropzone-prompt" class="flex flex-col items-center gap-2.5">
              <div class="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center shadow-inner">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
              </div>
              <div>
                <p id="prompt-main" class="text-sm font-semibold text-slate-700">Kéo thả tệp hoặc <span class="text-blue-600 underline">chọn từ máy</span></p>
                <p id="prompt-sub" class="text-xs text-slate-400 mt-0.5">Hỗ trợ JPG, JPEG, PDF đa trang, PNG, WebP</p>
              </div>
              <div class="flex items-center gap-2 mt-1">
                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 text-xs font-medium border border-blue-200">
                  <span>🖼️</span> Chọn JPG
                </span>
                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-red-50 text-red-700 text-xs font-medium border border-red-200">
                  <span>📑</span> Chọn PDF
                </span>
              </div>
            </div>

            <!-- Image preview for JPG, PNG, WebP -->
            <img id="image-preview" class="max-h-56 rounded-lg object-contain hidden border border-slate-200 shadow-sm" alt="Preview">

            <!-- PDF preview container -->
            <div id="pdf-preview" class="hidden flex flex-col items-center justify-center w-full gap-2">
              <div class="flex items-center gap-2 bg-red-50 text-red-700 px-3 py-1.5 rounded-lg border border-red-200 text-xs font-semibold">
                <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                </svg>
                <span id="pdf-badge">Tài liệu PDF</span>
              </div>
              <canvas id="pdf-canvas" class="hidden max-h-52 rounded-lg border border-slate-200 shadow-sm"></canvas>
              <p id="pdf-info" class="text-xs text-slate-500">Đang đọc tài liệu...</p>
            </div>
          </div>

          <!-- Main OCR Button Section (Always Prominent & Clickable) -->
          <div class="flex flex-col gap-2 pt-1">
            <button id="btn-submit" type="button" class="btn-ocr-action w-full py-3.5 px-6 rounded-xl text-base font-bold flex items-center justify-center gap-2.5 shadow-md transition cursor-pointer border-0">
              <svg id="btn-icon" class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
              <span id="btn-text">Bắt đầu nhận dạng OCR</span>
              <svg id="btn-spinner" class="animate-spin h-5 w-5 text-white hidden" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </button>
            <div class="flex items-center justify-between text-xs text-slate-500 px-1">
              <span id="file-info" class="truncate max-w-[220px]">Chưa chọn tệp (nhấn nút để tải tệp)</span>
              <span id="file-hint" class="text-blue-600 font-medium">Hỗ trợ JPG & PDF</span>
            </div>
          </div>
        </div>

        <!-- System specs info card -->
        <div class="bg-white p-4 rounded-xl border border-slate-200 text-xs text-slate-600 flex flex-col gap-2 shadow-sm">
          <div class="font-semibold text-slate-700 flex items-center justify-between">
            <span>Cấu hình mô hình</span>
            <span class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-mono">0.9B BF16</span>
          </div>
          <div class="grid grid-cols-2 gap-2 text-slate-500">
            <div>Kiến trúc: <span class="text-slate-800 font-medium">ERNIE 4.5 + SigLIP</span></div>
            <div>Tác vụ: <span class="text-slate-800 font-medium">Song ngữ Việt - Anh</span></div>
            <div>Hỗ trợ ảnh: <span class="text-slate-800 font-medium">JPG, JPEG, PNG, WebP</span></div>
            <div>Hỗ trợ tài liệu: <span class="text-slate-800 font-medium">PDF đơn/đa trang</span></div>
          </div>
        </div>
      </div>

      <!-- Right Column: Result Viewer (7 cols) -->
      <div class="lg:col-span-7 flex flex-col gap-4">
        <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex-1 flex flex-col min-h-[460px]">
          <!-- Results Header & Tabs -->
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center space-x-2">
              <button id="tab-text" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-50 text-blue-700">Văn bản trích xuất</button>
              <button id="tab-json" class="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:bg-slate-50">JSON chi tiết</button>
            </div>
            <div class="flex items-center space-x-2">
              <button id="btn-copy" class="text-xs text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 transition">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                <span>Sao chép</span>
              </button>
              <button id="btn-download" class="text-xs text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 transition">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                <span>Tải về</span>
              </button>
            </div>
          </div>

          <!-- Result Content Area -->
          <div class="relative flex-1 py-4 flex flex-col overflow-auto">
            <!-- Empty state -->
            <div id="result-empty" class="flex-1 flex flex-col items-center justify-center text-center text-slate-400 gap-2">
              <svg class="w-12 h-12 stroke-slate-300" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <p class="text-sm font-medium">Chưa có kết quả OCR</p>
              <p class="text-xs">Tải ảnh (JPG, PNG) hoặc tệp PDF lên và bấm "Trích xuất OCR" để xem kết quả.</p>
            </div>

            <!-- Loading overlay -->
            <div id="result-loading" class="hidden flex-1 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
              <p id="loading-msg" class="text-sm font-medium text-slate-700">Mô hình đang trích xuất dữ liệu...</p>
              <p id="timer" class="text-xs font-mono text-slate-500">Thời gian: 0s</p>
            </div>

            <!-- Text Tab Content -->
            <div id="content-text" class="hidden flex-1 flex flex-col">
              <div class="bg-slate-50 border border-slate-200 p-4 rounded-xl text-slate-800 font-mono text-sm leading-relaxed overflow-y-auto max-h-[500px]">
                <pre id="text-output" class="whitespace-pre-wrap"></pre>
              </div>
            </div>

            <!-- JSON Tab Content -->
            <div id="content-json" class="hidden flex-1 flex flex-col">
              <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl text-emerald-400 font-mono text-xs overflow-y-auto max-h-[500px]">
                <pre id="json-output"></pre>
              </div>
            </div>
          </div>

          <!-- Bottom Footer Info -->
          <div id="result-meta" class="hidden pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div class="flex items-center gap-3">
              <span id="timing-badge">Thời gian xử lý: -</span>
              <span id="pages-badge" class="hidden bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">1 trang</span>
            </div>
            <span id="model-badge">Engine: PaddleOCR-VL-1.6</span>
          </div>
        </div>
      </div>
    </div>
  </main>

  <script>
    if (window.pdfjsLib) {
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }

    let currentBase64 = null;
    let currentFileName = null;
    let lastResult = null;
    let timerInterval = null;

    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const preview = document.getElementById('image-preview');
    const pdfPreview = document.getElementById('pdf-preview');
    const pdfCanvas = document.getElementById('pdf-canvas');
    const pdfBadge = document.getElementById('pdf-badge');
    const pdfInfo = document.getElementById('pdf-info');
    const promptEl = document.getElementById('dropzone-prompt');
    const fileInfo = document.getElementById('file-info');
    const btnSubmit = document.getElementById('btn-submit');
    const btnText = document.getElementById('btn-text');
    const btnIcon = document.getElementById('btn-icon');
    const btnSpinner = document.getElementById('btn-spinner');
    const loadingMsg = document.getElementById('loading-msg');

    const tabModeAll = document.getElementById('tab-mode-all');
    const tabModePdf = document.getElementById('tab-mode-pdf');
    const tabModeJpg = document.getElementById('tab-mode-jpg');

    const btnSample = document.getElementById('btn-sample');
    const btnSampleJpg = document.getElementById('btn-sample-jpg');
    const btnSamplePdf = document.getElementById('btn-sample-pdf');

    const resultEmpty = document.getElementById('result-empty');
    const resultLoading = document.getElementById('result-loading');
    const contentText = document.getElementById('content-text');
    const contentJson = document.getElementById('content-json');
    const textOutput = document.getElementById('text-output');
    const jsonOutput = document.getElementById('json-output');
    const resultMeta = document.getElementById('result-meta');
    const timingBadge = document.getElementById('timing-badge');
    const pagesBadge = document.getElementById('pages-badge');
    const tabText = document.getElementById('tab-text');
    const tabJson = document.getElementById('tab-json');
    const timerEl = document.getElementById('timer');

    // Health Check
    fetch('/healthz')
      .then(r => r.json())
      .then(d => {
        document.getElementById('backend-status').textContent = `${d.model_id} (${d.status})`;
      })
      .catch(() => {
        document.getElementById('backend-status').textContent = 'Mất kết nối máy chủ';
      });

    // Mode Switching
    function setActiveMode(mode) {
      tabModeAll.className = "flex-1 py-1.5 px-2 font-medium rounded-lg text-slate-600 hover:text-slate-900 transition";
      tabModePdf.className = "flex-1 py-1.5 px-2 font-medium rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1";
      tabModeJpg.className = "flex-1 py-1.5 px-2 font-medium rounded-lg text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1";

      if (mode === 'pdf') {
        tabModePdf.className = "flex-1 py-1.5 px-2 font-semibold rounded-lg bg-white text-slate-800 shadow-sm transition flex items-center justify-center gap-1";
        fileInput.accept = ".pdf,application/pdf";
      } else if (mode === 'jpg') {
        tabModeJpg.className = "flex-1 py-1.5 px-2 font-semibold rounded-lg bg-white text-slate-800 shadow-sm transition flex items-center justify-center gap-1";
        fileInput.accept = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";
      } else {
        tabModeAll.className = "flex-1 py-1.5 px-2 font-semibold rounded-lg bg-white text-slate-800 shadow-sm transition";
        fileInput.accept = ".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf";
      }
    }

    tabModeAll.addEventListener('click', () => setActiveMode('all'));
    tabModePdf.addEventListener('click', () => { setActiveMode('pdf'); fileInput.click(); });
    tabModeJpg.addEventListener('click', () => { setActiveMode('jpg'); fileInput.click(); });

    // File Selection
    dropzone.addEventListener('click', (e) => {
      fileInput.click();
    });

    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      handleFiles(e.dataTransfer.files);
    });

    function handleFiles(files) {
      if (!files || files.length === 0) return;
      const file = files[0];
      currentFileName = file.name;
      const lower = file.name.toLowerCase();
      const isPdf = lower.endsWith('.pdf') || file.type === 'application/pdf';
      const sizeStr = (file.size / 1024).toFixed(1) + ' KB';
      
      fileInfo.textContent = `${file.name} (${sizeStr})`;
      promptEl.classList.add('hidden');
      btnSubmit.classList.add('btn-ocr-ready');
      btnText.textContent = isPdf ? `⚡ Bắt đầu OCR: ${file.name}` : `⚡ Bắt đầu OCR: ${file.name}`;

      const reader = new FileReader();
      reader.onload = (e) => {
        const fullUrl = e.target.result;
        currentBase64 = fullUrl.split(',')[1];

        if (isPdf) {
          preview.classList.add('hidden');
          pdfPreview.classList.remove('hidden');
          pdfBadge.textContent = 'Tài liệu PDF';
          pdfInfo.textContent = `${file.name} · ${sizeStr}`;

          // Try rendering first page of PDF using PDF.js
          if (window.pdfjsLib) {
            const rawData = atob(currentBase64);
            const rawLength = rawData.length;
            const array = new Uint8Array(new ArrayBuffer(rawLength));
            for (let i = 0; i < rawLength; i++) {
              array[i] = rawData.charCodeAt(i);
            }

            pdfjsLib.getDocument({ data: array }).promise.then(pdf => {
              pdfBadge.textContent = `Tài liệu PDF (${pdf.numPages} trang)`;
              pdfInfo.textContent = `${file.name} · ${sizeStr} · ${pdf.numPages} trang`;

              pdf.getPage(1).then(page => {
                const viewport = page.getViewport({ scale: 0.55 });
                const context = pdfCanvas.getContext('2d');
                pdfCanvas.height = viewport.height;
                pdfCanvas.width = viewport.width;
                pdfCanvas.classList.remove('hidden');

                const renderContext = {
                  canvasContext: context,
                  viewport: viewport
                };
                page.render(renderContext);
              });
            }).catch(err => {
              console.warn('PDF.js preview could not render:', err);
              pdfCanvas.classList.add('hidden');
            });
          }
        } else {
          pdfPreview.classList.add('hidden');
          pdfCanvas.classList.add('hidden');
          preview.src = fullUrl;
          preview.classList.remove('hidden');
        }
      };
      reader.readAsDataURL(file);
    }

    // Sample button loaders
    async function loadSampleFile(url, defaultName, mimeType) {
      fileInfo.textContent = `Đang nạp tệp mẫu ${defaultName}...`;
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Không tải được tệp mẫu');
        const blob = await res.blob();
        const file = new File([blob], defaultName, { type: mimeType });
        handleFiles([file]);
      } catch (e) {
        alert('Lỗi nạp tệp mẫu: ' + e.message);
      }
    }

    btnSample.addEventListener('click', (e) => {
      e.stopPropagation();
      loadSampleFile('/sample-image', 'sample_vn_invoice.png', 'image/png');
    });

    btnSampleJpg.addEventListener('click', (e) => {
      e.stopPropagation();
      loadSampleFile('/sample-jpg', 'sample_vn_invoice.jpg', 'image/jpeg');
    });

    btnSamplePdf.addEventListener('click', (e) => {
      e.stopPropagation();
      loadSampleFile('/sample-pdf', 'sample_vn_document.pdf', 'application/pdf');
    });

    // OCR Submission
    btnSubmit.addEventListener('click', async () => {
      if (!currentBase64) {
        // Direct guidance: open file selector when no file is chosen yet
        fileInput.click();
        return;
      }
      
      const isPdf = (currentFileName || '').toLowerCase().endsWith('.pdf');
      btnSubmit.disabled = true;
      btnIcon.classList.add('hidden');
      btnSpinner.classList.remove('hidden');
      btnText.textContent = isPdf ? 'Đang nhận dạng PDF...' : 'Đang xử lý OCR...';
      loadingMsg.textContent = isPdf 
        ? 'Mô hình đang phân tích và trích xuất tài liệu PDF...' 
        : 'Mô hình đang trích xuất dữ liệu ảnh...';

      resultEmpty.classList.add('hidden');
      contentText.classList.add('hidden');
      contentJson.classList.add('hidden');
      resultMeta.classList.add('hidden');
      resultLoading.classList.remove('hidden');

      let startTime = Date.now();
      timerInterval = setInterval(() => {
        const secs = ((Date.now() - startTime) / 1000).toFixed(1);
        timerEl.textContent = `Thời gian: ${secs}s`;
      }, 200);

      try {
        const response = await fetch('/v1/ocr', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content_base64: currentBase64,
            filename: currentFileName || (isPdf ? "document.pdf" : "document.jpg"),
            mode: "vlm"
          })
        });

        clearInterval(timerInterval);
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || 'Lỗi xử lý OCR');
        }

        lastResult = data;
        const totalDuration = ((Date.now() - startTime) / 1000).toFixed(2);
        
        textOutput.textContent = data.markdown || "(Không có văn bản)";
        jsonOutput.textContent = JSON.stringify(data, null, 2);

        resultLoading.classList.add('hidden');
        showTab('text');
        resultMeta.classList.remove('hidden');
        timingBadge.textContent = `Thời gian xử lý: ${totalDuration}s`;

        // Calculate pages count if any
        if (data.blocks && data.blocks.length > 0) {
          const maxPage = Math.max(...data.blocks.map(b => b.page || 1));
          pagesBadge.textContent = `${maxPage} trang`;
          pagesBadge.classList.remove('hidden');
        } else {
          pagesBadge.classList.add('hidden');
        }

      } catch (err) {
        clearInterval(timerInterval);
        resultLoading.classList.add('hidden');
        resultEmpty.classList.remove('hidden');
        alert('Lỗi: ' + err.message);
      } finally {
        btnSubmit.disabled = false;
        btnSpinner.classList.add('hidden');
        btnIcon.classList.remove('hidden');
        btnText.textContent = currentFileName ? `⚡ Bắt đầu OCR: ${currentFileName}` : 'Bắt đầu nhận dạng OCR';
      }
    });

    // Tab Switching
    function showTab(type) {
      if (type === 'text') {
        contentText.classList.remove('hidden');
        contentJson.classList.add('hidden');
        tabText.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-50 text-blue-700";
        tabJson.className = "px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:bg-slate-50";
      } else {
        contentText.classList.add('hidden');
        contentJson.classList.remove('hidden');
        tabJson.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-50 text-blue-700";
        tabText.className = "px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:bg-slate-50";
      }
    }

    tabText.addEventListener('click', () => showTab('text'));
    tabJson.addEventListener('click', () => showTab('json'));

    // Copy & Download
    document.getElementById('btn-copy').addEventListener('click', () => {
      if (!lastResult) return;
      const isJsonActive = !contentJson.classList.contains('hidden');
      const textToCopy = isJsonActive ? JSON.stringify(lastResult, null, 2) : lastResult.markdown;
      navigator.clipboard.writeText(textToCopy);
      alert('Đã sao chép vào bộ nhớ đệm!');
    });

    document.getElementById('btn-download').addEventListener('click', () => {
      if (!lastResult) return;
      const isJsonActive = !contentJson.classList.contains('hidden');
      const content = isJsonActive ? JSON.stringify(lastResult, null, 2) : lastResult.markdown;
      const ext = isJsonActive ? 'json' : 'txt';
      const baseName = (currentFileName || 'ocr_result').replace(/\.[^/.]+$/, "");
      const filename = `${baseName}_result.${ext}`;
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    });
  </script>
</body>
</html>
"""
