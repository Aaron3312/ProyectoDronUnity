import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const SecurityDashboard = () => {
  const generateData = () => {
    const data = [];
    for (let i = 0; i < 10; i++) {
      data.push({
        minuto: i + 1,
        camara1: Math.floor(Math.random() * (5 - 2) + 2),
        camara2: Math.floor(Math.random() * (4 - 1) + 1),
        camara3: Math.floor(Math.random() * (5 - 2) + 2),
        camara4: Math.floor(Math.random() * (4 - 1) + 1),
        dron: Math.floor(Math.random() * (2 - 0) + 0),
        agente: Math.floor(Math.random() * 2)
      });
    }
    return data;
  };

  const data = generateData();

  const calcularUtilidad = (agente) => {
    const totalDetecciones = data.reduce((sum, item) => sum + item[agente], 0);
    return (totalDetecciones / 10).toFixed(2);
  };

  const utilidades = {
    camaras: ((data.reduce((sum, item) => 
      sum + item.camara1 + item.camara2 + item.camara3 + item.camara4, 0)) / 40).toFixed(2),
    dron: calcularUtilidad('dron'),
    agente: calcularUtilidad('agente')
  };

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-4">
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Detecciones por Cámaras</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="minuto" label={{ value: 'Minuto', position: 'bottom' }} />
              <YAxis label={{ value: 'Detecciones', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="camara1" stroke="#8884d8" />
              <Line type="monotone" dataKey="camara2" stroke="#82ca9d" />
              <Line type="monotone" dataKey="camara3" stroke="#ffc658" />
              <Line type="monotone" dataKey="camara4" stroke="#ff7300" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Detecciones Dron y Agente</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="minuto" label={{ value: 'Minuto', position: 'bottom' }} />
              <YAxis label={{ value: 'Detecciones', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="dron" stroke="#8884d8" />
              <Line type="monotone" dataKey="agente" stroke="#82ca9d" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Utilidad Final (Detecciones/Tiempo)</h2>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-4 bg-blue-100 rounded">
            <div className="text-lg font-bold">Cámaras</div>
            <div className="text-2xl">{utilidades.camaras}</div>
          </div>
          <div className="p-4 bg-green-100 rounded">
            <div className="text-lg font-bold">Dron</div>
            <div className="text-2xl">{utilidades.dron}</div>
          </div>
          <div className="p-4 bg-yellow-100 rounded">
            <div className="text-lg font-bold">Agente</div>
            <div className="text-2xl">{utilidades.agente}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SecurityDashboard;