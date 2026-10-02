import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles/dashboard.css';
import './styles/prototype.css';

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);
