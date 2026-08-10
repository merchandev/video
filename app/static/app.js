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
    const inputs = ['image', 'end_image', 'video', 'storyboard_images'];
    inputs.forEach(id => {
        const input = document.getElementById(id);
        const msg = document.getElementById(`msg-${id.replace('_', '-')}`);
        if(input && msg) {
            input.addEventListener('change', (e) => {
                const count = e.target.files.length;
                if (count > 0) {
                    msg.textContent = count === 1 ? e.target.files[0].name : `${count} archivos seleccionados`;
                    msg.style.color = '#a29bfe';
                    if (count > 20) {
                        alert(`Has seleccionado ${count} archivos. Solo se procesarán los primeros 20 para evitar sobrecarga.`);
                    }
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

    const durationLabel = document.querySelector('label[for="duration_seconds"]');

    const groupStoryboard = document.getElementById('group-storyboard');

    // Mode logic
    modeSelect.addEventListener('change', (e) => {
        const mode = e.target.value;
        groupImage.classList.add('hidden');
        groupEndImage.classList.add('hidden');
        groupVideo.classList.add('hidden');
        if (groupStoryboard) groupStoryboard.classList.add('hidden');
        
        if (durationLabel) {
            if (mode === 'extend') {
                durationLabel.textContent = 'Duración adicional a generar (segundos)';
            } else if (mode === 'storyboard') {
                durationLabel.textContent = 'Duración total del video (segundos)';
            } else {
                durationLabel.textContent = 'Duración (segundos)';
            }
        }
        
        if (mode === 'i2v') {
            groupImage.classList.remove('hidden');
        } else if (mode === 't2v') {
            // Solo prompt
        } else if (mode === 'first_last') {
            groupImage.classList.remove('hidden');
            groupEndImage.classList.remove('hidden');
        } else if (mode === 'extend') {
            groupVideo.classList.remove('hidden');
        } else if (mode === 'storyboard' && groupStoryboard) {
            groupStoryboard.classList.remove('hidden');
        }
    });

    // States
    const emptyState = document.getElementById('empty-state');
    const jobsGrid = document.getElementById('jobs-grid');
    const submitBtn = document.getElementById('generate-btn');

    let activeJobs = []; // [{id: "uuid", status: "queued", interval: 123}, ...]

    function createJobCard(jobId, index) {
        const card = document.createElement('div');
        card.className = 'job-card';
        card.id = `job-${jobId}`;
        card.innerHTML = `
            <div class="job-header">
                <div class="job-title">Video #${index + 1}</div>
                <div class="job-status queued" id="status-${jobId}">En cola</div>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" id="progress-${jobId}" style="width: 0%"></div>
            </div>
            <div class="log-container hidden" id="log-${jobId}"></div>
            <video id="video-${jobId}" class="job-video hidden" controls loop autoplay playsinline></video>
            <div class="job-actions hidden" id="actions-${jobId}">
                <a href="#" id="dl-mp4-${jobId}" class="btn-secondary" download>MP4</a>
                <a href="#" id="dl-json-${jobId}" class="btn-secondary" download>JSON</a>
            </div>
            <button class="btn-danger" id="cancel-${jobId}" style="margin-top:0.5rem; font-size:0.8rem; padding:0.5rem;">Cancelar</button>
        `;
        jobsGrid.appendChild(card);
        
        document.getElementById(`cancel-${jobId}`).addEventListener('click', async () => {
            try {
                const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
                if (!res.ok) {
                    // 409 = job already finished — refresh its real status
                    await pollJob(jobId);
                    return;
                }
                document.getElementById(`status-${jobId}`).textContent = 'Cancelado';
                document.getElementById(`status-${jobId}`).className = 'job-status failed';
            } catch (error) {
                console.error(error);
            }
        });
        
        emptyState.classList.add('hidden');
        jobsGrid.classList.remove('hidden');
    }

    async function pollJob(jobId) {
        try {
            const res = await fetch(`/api/jobs/${jobId}`);
            if (!res.ok) return;
            
            const data = await res.json();
            const jobItem = activeJobs.find(j => j.id === jobId);
            if (!jobItem) return;

            const statusEl = document.getElementById(`status-${jobId}`);
            const progressEl = document.getElementById(`progress-${jobId}`);
            
            if (data.status === 'queued') {
                statusEl.textContent = 'En cola';
                statusEl.className = 'job-status queued';
            } else if (data.status === 'processing') {
                statusEl.textContent = 'Procesando...';
                statusEl.className = 'job-status processing';
                progressEl.style.width = `${Math.max(5, data.progress * 100)}%`;
            } else if (data.status === 'completed') {
                statusEl.textContent = 'Completado';
                statusEl.className = 'job-status completed';
                progressEl.style.width = '100%';
                
                // Mostrar video y ocultar barra
                progressEl.parentElement.classList.add('hidden');
                document.getElementById(`cancel-${jobId}`).classList.add('hidden');
                
                const vidEl = document.getElementById(`video-${jobId}`);
                vidEl.src = `${data.video_url}?t=${new Date().getTime()}`;
                vidEl.classList.remove('hidden');
                
                const actionsEl = document.getElementById(`actions-${jobId}`);
                actionsEl.classList.remove('hidden');
                document.getElementById(`dl-mp4-${jobId}`).href = data.video_url;
                
                const jsonBlob = new Blob([JSON.stringify(data.params, null, 2)], {type: 'application/json'});
                const jsonUrl = URL.createObjectURL(jsonBlob);
                document.getElementById(`dl-json-${jobId}`).href = jsonUrl;
                document.getElementById(`dl-json-${jobId}`).download = `${data.id}.json`;
                
                clearInterval(jobItem.interval);
            } else if (data.status === 'failed' || data.status === 'cancelled') {
                statusEl.textContent = data.status === 'failed' ? 'Error' : 'Cancelado';
                statusEl.className = 'job-status failed';
                progressEl.parentElement.classList.add('hidden');
                document.getElementById(`cancel-${jobId}`).classList.add('hidden');
                
                if (data.error) {
                    const logEl = document.getElementById(`log-${jobId}`);
                    logEl.textContent = `Error: ${data.error}`;
                    logEl.classList.remove('hidden');
                }
                clearInterval(jobItem.interval);
            }
        } catch (error) {
            console.error('Error polling:', error);
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        submitBtn.disabled = true;
        submitBtn.textContent = "COMPROBANDO MODELO...";
        
        const baseFormData = new FormData(form);
        const mode = baseFormData.get('mode');
        
        try {
            const statusRes = await fetch("/api/readiness");
            if (statusRes.ok) {
                const statusData = await statusRes.json();
                if (statusData.models) {
                    let isReady = false;
                    const duration = Number(baseFormData.get('duration_seconds')) || 4;
                    if (mode === 'i2v' && duration <= 4) {
                        isReady = statusData.models.i2v && statusData.models.i2v.ready;
                    } else {
                        isReady = statusData.models.df && statusData.models.df.ready;
                    }
                    
                    if (!isReady) {
                        alert("MODELO INCOMPLETO.\n\nEspera a que termine la descarga antes de generar.");
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = 'GENERAR VIDEOS <span class="btn-glow"></span>';
                        return;
                    }
                }
            }
        } catch (err) {
            console.error("No se pudo comprobar el modelo", err);
        }

        submitBtn.textContent = "ENVIANDO LOTE...";
        
        // Cada modo produce SIEMPRE 1 solo job.
        // I2V / first_last / extend / t2v / storyboard → 1 video.
        let jobFiles = null; // datos de archivos para el único job

        if (mode === 'i2v') {
            const input = document.getElementById('image');
            if (input.files.length > 0) jobFiles = { image: input.files[0] };
        } else if (mode === 'extend') {
            const input = document.getElementById('video');
            if (input.files.length > 0) jobFiles = { video: input.files[0] };
        } else if (mode === 'first_last') {
            const imgInput = document.getElementById('image');
            const endImgInput = document.getElementById('end_image');
            if (imgInput.files.length > 0 && endImgInput.files.length > 0) {
                jobFiles = { start: imgInput.files[0], end: endImgInput.files[0] };
            }
        } else if (mode === 'storyboard') {
            const input = document.getElementById('storyboard_images');
            if (input.files.length >= 2) {
                jobFiles = { storyboard: Array.from(input.files).slice(0, 20) };
            } else {
                alert("Storyboard requiere al menos 2 archivos (imágenes o videos).");
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'GENERAR VIDEO <span class="btn-glow"></span>';
                return;
            }
        }
        
        // 1 solo job siempre
        const jobFormData = new FormData();
        const fileKeys = ['image', 'end_image', 'video', 'storyboard_images'];
        for (const [key, value] of baseFormData.entries()) {
            if (!fileKeys.includes(key)) {
                jobFormData.append(key, value);
            }
        }

        if (mode === 'i2v' && jobFiles?.image) {
            jobFormData.append('image', jobFiles.image);
        } else if (mode === 'extend' && jobFiles?.video) {
            jobFormData.append('video', jobFiles.video);
        } else if (mode === 'first_last' && jobFiles?.start) {
            jobFormData.append('image', jobFiles.start);
            jobFormData.append('end_image', jobFiles.end);
        } else if (mode === 'storyboard' && jobFiles?.storyboard) {
            for (const f of jobFiles.storyboard) {
                jobFormData.append('storyboard_images', f);
            }
        }
        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                body: jobFormData
            });
            
            if (res.ok) {
                const data = await res.json();
                createJobCard(data.job_id, 0);
                
                const interval = setInterval(() => pollJob(data.job_id), 3000);
                activeJobs.push({ id: data.job_id, status: 'queued', interval: interval });
            } else {
                const errData = await res.json();
                let detailMsg = errData.detail;
                if (typeof detailMsg === 'object') {
                    if (Array.isArray(detailMsg)) {
                        detailMsg = detailMsg.map(d => `${d.loc ? d.loc.join('->') + ': ' : ''}${d.msg}`).join('\n');
                    } else {
                        detailMsg = JSON.stringify(detailMsg);
                    }
                }
                alert(`Error al enviar:\n${detailMsg || 'Petición rechazada'}`);
            }
        } catch (err) {
            console.error("Error submitting job", err);
            alert(`Error de red al enviar el video`);
        }
        
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'GENERAR VIDEO <span class="btn-glow"></span>';
        
        // Limpiar el form para permitir otro lote nuevo
        form.reset();
        document.querySelectorAll('.file-msg').forEach(el => {
            el.textContent = 'Seleccionar archivo...';
            el.style.color = '';
        });
    });
});
