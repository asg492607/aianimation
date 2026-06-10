const API_BASE = 'http://localhost:8000/api/v1';

// ---- CREATE PAGE LOGIC ----
const createForm = document.getElementById('createForm');
if (createForm) {
  createForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('title').value;
    const prompt = document.getElementById('prompt').value;
    const style = document.getElementById('style').value;
    const profile = document.getElementById('profile').value;
    const btn = createForm.querySelector('button');
    
    btn.textContent = 'Initializing...';
    btn.disabled = true;

    try {
      // Step 1: In a real app, you would POST /projects to create the DB record first.
      // Since our MVP endpoint is POST /projects/{id}/generate, we will generate a mock UUID
      // or assume the backend creates one if not found. For this frontend MVP, let's generate a random UUID to pass.
      const projectId = crypto.randomUUID();
      
      const res = await fetch(`${API_BASE}/projects/${projectId}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          title, 
          prompt,
          meta: {
            requested_style: style,
            render_profile: profile
          }
        })
      });

      if (res.ok) {
        // Redirect to monitor page
        window.location.href = `monitor.html?id=${projectId}`;
      } else {
        alert('Failed to start generation. Make sure backend is running.');
        btn.textContent = 'Generate Magic';
        btn.disabled = false;
      }
    } catch (err) {
      console.error(err);
      alert('Network error connecting to backend.');
      btn.textContent = 'Generate Magic';
      btn.disabled = false;
    }
  });
}

// ---- MONITOR PAGE LOGIC ----
const logBox = document.getElementById('logBox');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');
const currentStatus = document.getElementById('currentStatus');
const resultContainer = document.getElementById('resultContainer');

if (logBox) {
  const urlParams = new URLSearchParams(window.location.search);
  const projectId = urlParams.get('id');

  if (!projectId) {
    window.location.href = 'index.html';
  } else {
    connectWebSocket(projectId);
  }
}

function connectWebSocket(projectId) {
  // Get token from localStorage (assuming standard login flow)
  const token = localStorage.getItem('access_token') || 'test_token';
  
  // Determine ws protocol based on http
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Use localhost for local dev, or dynamic host
  const wsUrl = `ws://localhost:8000/api/v1/ws/projects/${projectId}?token=${token}`;
  
  const ws = new WebSocket(wsUrl);

  const pipelineSteps = [
    'DirectorAgent', 'ScriptAgent', 'CharacterAgent', 'SceneAgent', 
    'StoryboardAgent', 'CameraAgent', 'AssetAgent', 'VoiceAgent', 
    'MusicAgent', 'TimelineAgent', 'RenderAgent', 'ExportAgent', 'Orchestrator'
  ];

  ws.onopen = () => {
    appendLog('WebSocket connected successfully.');
    currentStatus.textContent = 'Waiting for Director...';
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.event === 'progress') {
      const { agent, status } = data;
      appendLog(`[${new Date().toLocaleTimeString()}] ${agent} -> ${status}`);
      
      currentStatus.textContent = `${agent} is ${status.toLowerCase()}...`;
      
      // Calculate progress percentage
      const stepIndex = pipelineSteps.indexOf(agent);
      if (stepIndex !== -1) {
        let percent = Math.round((stepIndex / pipelineSteps.length) * 100);
        if (status === 'COMPLETED' && agent === 'Orchestrator') percent = 100;
        
        progressFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        
        if (percent === 100) {
          currentStatus.textContent = 'Generation Complete!';
          resultContainer.style.display = 'block';
          ws.close();
        }
      }
    }
  };

  ws.onerror = (err) => {
    console.error('WebSocket error', err);
    appendLog('WebSocket encountered an error.', true);
  };

  ws.onclose = () => {
    appendLog('WebSocket connection closed.');
  };
}

function appendLog(msg, isError = false) {
  const div = document.createElement('div');
  div.textContent = '> ' + msg;
  if (isError) div.style.color = '#ef4444';
  logBox.appendChild(div);
  logBox.scrollTop = logBox.scrollHeight;
}
