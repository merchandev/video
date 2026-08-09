document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generate-form');
    const advancedToggle = document.getElementById('advanced-toggle');
    const advancedSettings = document.getElementById('advanced-settings');
    const modeSelect = document.getElementById('mode');
    
    // Groups
    const groupImage = document.getElementById('group-image');
    const groupEndImage = document.getElementById('group-end-image');
    const groupVideo = document.getElementById('group-video');
    
    // File inputs
    const inputs = ['image', 'end_image', 'video'];
    inputs.forEach(id => {
        const input = document.getElementById(id);
        const msg = document.getElementById(`msg-${id.replace('_', '-')}`);
        if(input && msg) {
            input.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    msg.textContent = e.target.files[0].name;
                    msg.style.color = '#a29bfe';
                } else {
                    msg.textContent = 'Seleccionar archivo...';
                    msg.style.color = '';
                }
            });
        }
    });

    // Toggle advanced settings
    advancedToggle.addEventListener('click', () => {
        advancedToggle.classList.toggle('open');
        advancedSettings.classList.toggle('open');
    });

    // Mode logic
    modeSelect.addEventListener('change', (e) => {
        const mode = e.target.value;
        groupImage.classList.add('hidden');
        groupEndImage.classList.add('hidden');
        groupVideo.classList.add('hidden');
        
        if (mode === 'i2v') {
            groupImage.classList.remove('hidden');
        } else if (mode === 't2v') {
            // Solo prompt
        } else if (mode === 'first_last') {
            groupImage.classList.remove('hidden');
            groupEndImage.classList.remove('hidden');
        } else if (mode === 'extend') {
            groupVideo.classList.remove('hidden');
        }
    });

    // States
    const emptyState = document.getElementById('empty-state');
    const progressState = document.getElementById('progress-state');
    const resultState = document.getElementById('result-state');
    
    const progressBar = document.getElementById('progress-bar');
    const logContainer = document.getElementById('log-container');
    const cancelBtn = document.getElementById('cancel-btn');
    const progressText = document.getElementById('progress-text');
    
    const resultVideo = document.getElementById('result-video');
    const downloadMp4 = document.getElementById('download-mp4');
    const downloadJson = document.getElementById('download-json');
    const submitBtn = document.getElementById('generate-btn');

    let currentJobId = null;
    let pollInterval = null;

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

    async function pollJob(jobId) {
        try {
            const res = await fetch(`/api/jobs/${jobId}`);
            if (!res.ok) throw new Error('Error al consultar el trabajo');
            
            const data = await res.json();
            
            // Fake progress since native diffusers doesn't give us streaming % yet
            let currentPct = parseFloat(progressBar.style.width) || 5;
            if (data.status === 'processing' && currentPct < 90) {
                currentPct += 2;
            }
            
            progressBar.style.width = `${currentPct}%`;
            
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                finishJob(data);
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                progressText.textContent = 'Fallo en la generación';
                progressText.style.color = 'var(--danger)';
                appendLog([data.error || 'Unknown error']);
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
        resultVideo.src = `${data.video_url}?t=${new Date().getTime()}`;
        downloadMp4.href = data.video_url;
        
        const jsonBlob = new Blob([JSON.stringify(data.params, null, 2)], {type: 'application/json'});
        downloadJson.href = URL.createObjectURL(jsonBlob);
        downloadJson.download = `${data.id}_metadata.json`;

        showState('result');
        submitBtn.disabled = false;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        submitBtn.disabled = true;
        showState('progress');
        progressBar.style.width = '2%';
        progressText.textContent = 'Generando en background...';
        progressText.style.color = 'var(--accent-hover)';
        logContainer.innerHTML = '';
        
        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                body: formData
            });
            
            if (!res.ok) throw new Error('Error de servidor');
            
            const data = await res.json();
            currentJobId = data.job_id;
            
            pollInterval = setInterval(() => pollJob(currentJobId), 3000);
            
        } catch (error) {
            console.error(error);
            alert('Error: No se pudo iniciar el proceso.');
            showState('empty');
            submitBtn.disabled = false;
        }
    });

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
