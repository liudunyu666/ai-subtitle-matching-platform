import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE + '/api',
  timeout: 120000,
});

export { API_BASE };

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.msg || err.message || '请求失败';
    return Promise.reject(new Error(msg));
  }
);

export function createTask(formData) {
  return api.post('/tasks', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function getTask(taskId) {
  return api.get(`/tasks/${taskId}`);
}

export function listTasks() {
  return api.get('/tasks');
}

export function updateSegments(taskId, segments) {
  return api.put(`/tasks/${taskId}/segments`, { segments });
}

export function selectMaterial(taskId, segId, materialId) {
  return api.post(`/tasks/${taskId}/segments/${segId}/select`, { material_id: materialId });
}

export function listMaterials(keyword) {
  const params = keyword ? { keyword } : {};
  return api.get('/materials', { params });
}

export function uploadMaterial(formData) {
  return api.post('/materials', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function deleteMaterial(id) {
  return api.delete(`/materials/${id}`);
}

export function parseSubtitle(text) {
  return api.post('/parse-subtitle', { text });
}

export function retryTask(taskId) {
  return api.post(`/tasks/${taskId}/retry`);
}

export function suggestTags(name) {
  return api.get('/materials/suggest-tags', { params: { name } });
}
