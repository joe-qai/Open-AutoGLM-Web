import api from './api';

export const controlApi = {
  touchDown: (deviceId: string, x: number, y: number) =>
    api.post(`/api/v1/control/${deviceId}/touch`, { x, y, action: 'down' }),
  
  touchMove: (deviceId: string, x: number, y: number) =>
    api.post(`/api/v1/control/${deviceId}/touch`, { x, y, action: 'move' }),
  
  touchUp: (deviceId: string, x: number, y: number) =>
    api.post(`/api/v1/control/${deviceId}/touch`, { x, y, action: 'up' }),
  
  tap: (deviceId: string, x: number, y: number) =>
    api.post(`/api/v1/control/${deviceId}/tap`, { x, y }),
  
  swipe: (deviceId: string, startX: number, startY: number, endX: number, endY: number) =>
    api.post(`/api/v1/control/${deviceId}/swipe`, { start_x: startX, start_y: startY, end_x: endX, end_y: endY }),
  
  typeText: (deviceId: string, text: string) =>
    api.post(`/api/v1/control/${deviceId}/type`, { text }),
  
  back: (deviceId: string) =>
    api.post(`/api/v1/control/${deviceId}/back`),
  
  home: (deviceId: string) =>
    api.post(`/api/v1/control/${deviceId}/home`),
  
  recent: (deviceId: string) =>
    api.post(`/api/v1/control/${deviceId}/recent`),
  
  volumeUp: (deviceId: string) =>
    api.post(`/api/v1/control/${deviceId}/volume_up`),
  
  volumeDown: (deviceId: string) =>
    api.post(`/api/v1/control/${deviceId}/volume_down`),
  
  power: (deviceId: string) =>
    api.post(`/api/v1/control/${deviceId}/power`),
};

export default controlApi;
