document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generate-form');
    const advancedToggle = document.getElementById('advanced-toggle');
    const advancedSettings = document.getElementById('advanced-settings');
    const fileInput = document.getElementById('image');
    const fileMsg = document.querySelector('.file-msg');
    
    // States
    const emptyState = document.getElementById('empty-state');
    const progressState = document.getElementById('progress-state');
    const resultState = document.getElementById('result-state');
    
    // Progress elements
    const progressBar = document.getElementById('progress-bar');
    const logContainer = document.getElementById('log-container');
    const cancelBtn = document.getElementById('cancel-btn');
    const progressText = document.getElementById('progress-text');
    
    // Result elements
    const resultVideo = document.getElementById('result-video');
    const downloadMp4 = document.getElementById('download-mp4');
    const downloadJson = document.getElementById('download-json');
    const submitBtn = document.getElementById('generate-btn');

    let currentJobId = null;
    let pollInterval = null;

    // Toggle advanced settings
    advancedToggle.addEventListener('click', () => {
        advancedToggle.classList.toggle('open');
        advancedSettings.classList.toggle('open');
    });

    // File input UX
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileMsg.textContent = e.target.files[0].name;
            fileMsg.style.color = '#a29bfe';
        } else {
            fileMsg.textContent = 'Arrastra tu imagen o haz clic aquí';
            fileMsg.style.color = '';
        }
    });

    // UI State Management
    function showState(state) {
        emptyState.classList.add('hidden');
        progressState.classList.add('hidden');
        resultState.classList.add('hidden');

        if (state === 'empty') emptyState.classList.remove('hidden');
        if (state === 'progress') progressState.classList.remove('hidden');
        if (state === 'result') resultState.classList.remove('hidden');
    }

    function appendLog(logs) {
        logContainer.innerHTML = '';
        logs.forEach(log => {
            const div = document.createElement('div');
            div.textContent = `> ${log}`;
            logContainer.appendChild(div);
        });
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Polling function
    async function pollJob(jobId) {
        try {
            const res = await fetch(`/api/jobs/${jobId}`);
            if (!res.ok) throw new Error('Error al consultar el trabajo');
            
            const data = await res.json();
            
            // Update progress
            const pct = Math.max(5, Math.min(100, data.progress * 100));
            progressBar.style.width = `${pct}%`;
            
            if (data.log && data.log.length > 0) {
                appendLog(data.log);
            }

            if (data.status === 'completed') {
                clearInterval(pollInterval);
                finishJob(data);
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                progressText.textContent = 'Fallo en la generación';
                progressText.style.color = 'var(--danger)';
                submitBtn.disabled = false;
            } else if (data.status === 'cancelled') {
                clearInterval(pollInterval);
                progressText.textContent = 'Generación Cancelada';
                progressText.style.color = 'var(--text-muted)';
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error polling:', error);
        }
    }

    function finishJob(data) {
        // Set video source
        // Agregar un timestamp para evitar cache
        resultVideo.src = `${data.video_url}?t=${new Date().getTime()}`;
        downloadMp4.href = data.video_url;
        
        // El JSON real se descarga al backend o creamos un Blob de params
        const jsonBlob = new Blob([JSON.stringify(data.params, null, 2)], {type: 'application/json'});
        downloadJson.href = URL.createObjectURL(jsonBlob);
        downloadJson.download = `${data.id}_metadata.json`;

        showState('result');
        submitBtn.disabled = false;
    }

    // Form Submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        submitBtn.disabled = true;
        showState('progress');
        progressBar.style.width = '2%';
        progressText.textContent = 'Enviando trabajo...';
        progressText.style.color = 'var(--accent-hover)';
        logContainer.innerHTML = '';
        
        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                body: formData
            });
            
            if (!res.ok) throw new Error('Error de servidor al iniciar la generación');
            
            const data = await res.json();
            currentJobId = data.job_id;
            
            progressText.textContent = 'Generando...';
            pollInterval = setInterval(() => pollJob(currentJobId), 2000);
            
        } catch (error) {
            console.error(error);
            alert('Error: No se pudo iniciar el proceso.');
            showState('empty');
            submitBtn.disabled = false;
        }
    });

    // Cancel Button
    cancelBtn.addEventListener('click', async () => {
        if (!currentJobId) return;
        
        try {
            await fetch(`/api/jobs/${currentJobId}/cancel`, { method: 'POST' });
            progressText.textContent = 'Cancelando...';
        } catch (error) {
            console.error(error);
        }
    });
});
