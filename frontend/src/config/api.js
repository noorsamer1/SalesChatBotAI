// API Configuration for Load Balancer Setup
const getApiBaseUrl = () => {
  const hostname = window.location.hostname;
  const port = window.location.port;
  
  // External access through load balancer (HTTPS -> HTTP nginx)
  if (hostname === '194.165.140.77') {
    return `https://${hostname}:${port}/api`;  // Browser sees HTTPS from load balancer
  }
  
  // Local development and internal access
  const protocol = window.location.protocol;
  return `${protocol}//${hostname}:${port}/api`;
};

export const API_BASE_URL = getApiBaseUrl();

console.log(`API Base URL: ${API_BASE_URL} (detected from hostname: ${window.location.hostname})`); 