// Dynamically determine the API Base URL based on where the frontend is hosted
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE = isLocalhost 
  ? 'http://localhost:8000/api/v1' 
  : 'https://aianimation.onrender.com/api/v1';
const WS_BASE = isLocalhost
  ? 'ws://localhost:8000/api/v1'
  : 'wss://aianimation.onrender.com/api/v1';

// ---- CREATE PAGE LOGIC ----
const createForm = document.getElementById('createForm');
if (createForm) {
  // Load Templates
  async function loadTemplates() {
    try {
      const res = await fetch(`${API_BASE}/templates/`);
      if (!res.ok) throw new Error('Failed to load templates');
      const templates = await res.json();
      
      const container = document.getElementById('templateContainer');
      container.innerHTML = templates.map(t => `
        <div class="template-card" style="min-width: 200px; background: rgba(15,23,42,0.6); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1rem; cursor: pointer; transition: 0.2s;" onclick="applyTemplate('${t.name}', \`${t.prompt_template}\`, '${t.category}')">
          <img src="${t.thumbnail_url}" style="width: 100%; height: 100px; object-fit: cover; border-radius: 4px; margin-bottom: 0.5rem;">
          <h4 style="margin: 0 0 0.25rem 0; font-size: 0.95rem;">${t.name}</h4>
          <p style="margin: 0; font-size: 0.8rem; color: var(--text-muted);">${t.description}</p>
        </div>
      `).join('');
    } catch(e) {
      console.error(e);
      document.getElementById('templateContainer').innerHTML = '<p>No templates available.</p>';
    }
  }
  
  window.applyTemplate = function(name, prompt, category) {
    document.getElementById('title').value = name;
    document.getElementById('prompt').value = prompt;
    // Map category to style if possible
    const styleMap = { "marketing": "Corporate", "explainer": "Legal Explainer", "educational": "Education" };
    if (styleMap[category]) {
      document.getElementById('style').value = styleMap[category];
    }
  };

  document.addEventListener('DOMContentLoaded', loadTemplates);

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
  const wsUrl = `${WS_BASE}/ws/projects/${projectId}?token=${token}`;
  
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
