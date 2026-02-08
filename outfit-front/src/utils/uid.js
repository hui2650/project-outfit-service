export const uid = () =>
  'id_' + Date.now() + '_' + Math.random().toString(16).slice(2)
