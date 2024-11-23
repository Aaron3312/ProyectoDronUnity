import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
	LineChart,
	Line,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	Legend,
	ResponsiveContainer,
	BarChart,
	Bar,
} from "recharts";

const MetricsDashboard = () => {
	const [metricsHistory, setMetricsHistory] = useState([]);
	const [currentMetrics, setCurrentMetrics] = useState([]);

	// Simular la recepción de datos en tiempo real
	useEffect(() => {
		const fetchMetrics = async () => {
			try {
				const response = await fetch("http://localhost:5000/get_decisions", {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
					},
					body: JSON.stringify({
						/* your world state here */
					}),
				});
				const data = await response.json();

				if (data.metrics) {
					setCurrentMetrics(data.metrics);
					setMetricsHistory((prev) => [
						...prev,
						{
							timestamp: new Date().toLocaleTimeString(),
							...data.metrics.reduce(
								(acc, metric) => ({
									...acc,
									[`Agent ${metric.agent_id}`]: metric.cubes_delivered,
								}),
								{}
							),
						},
					]);
				}
			} catch (error) {
				console.error("Error fetching metrics:", error);
			}
		};

		// Actualizar cada segundo
		const interval = setInterval(fetchMetrics, 1000);
		return () => clearInterval(interval);
	}, []);

	return (
		<div className="w-full max-w-6xl mx-auto p-4 space-y-4">
			<Card>
				<CardHeader>
					<CardTitle>Robot Performance Dashboard</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
						{/* Gráfico de líneas para cubos entregados en el tiempo */}
						<Card className="p-4">
							<CardHeader>
								<CardTitle className="text-lg">
									Cubos Entregados por Agente (Histórico)
								</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="h-64">
									<ResponsiveContainer width="100%" height="100%">
										<LineChart
											data={metricsHistory.slice(-20)}
											margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
										>
											<CartesianGrid strokeDasharray="3 3" />
											<XAxis dataKey="timestamp" />
											<YAxis />
											<Tooltip />
											<Legend />
											{currentMetrics.map((metric, index) => (
												<Line
													key={metric.agent_id}
													type="monotone"
													dataKey={`Agent ${metric.agent_id}`}
													stroke={`hsl(${index * 137.508}deg, 70%, 50%)`}
													strokeWidth={2}
												/>
											))}
										</LineChart>
									</ResponsiveContainer>
								</div>
							</CardContent>
						</Card>

						{/* Gráfico de barras para eficiencia actual */}
						<Card className="p-4">
							<CardHeader>
								<CardTitle className="text-lg">
									Eficiencia Actual por Agente
								</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="h-64">
									<ResponsiveContainer width="100%" height="100%">
										<BarChart
											data={currentMetrics}
											margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
										>
											<CartesianGrid strokeDasharray="3 3" />
											<XAxis dataKey="agent_id" />
											<YAxis />
											<Tooltip />
											<Legend />
											<Bar
												dataKey="efficiency_ratio"
												fill="#8884d8"
												name="Eficiencia"
											/>
										</BarChart>
									</ResponsiveContainer>
								</div>
							</CardContent>
						</Card>

						{/* Tabla de métricas actuales */}
						<Card className="p-4 col-span-full">
							<CardHeader>
								<CardTitle className="text-lg">Métricas Detalladas</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="overflow-x-auto">
									<table className="w-full">
										<thead>
											<tr className="border-b">
												<th className="p-2 text-left">Agente ID</th>
												<th className="p-2 text-left">Cubos Entregados</th>
												<th className="p-2 text-left">Distancia Total</th>
												<th className="p-2 text-left">Ratio de Eficiencia</th>
												<th className="p-2 text-left">Tasa de Entrega</th>
											</tr>
										</thead>
										<tbody>
											{currentMetrics.map((metric) => (
												<tr key={metric.agent_id} className="border-b">
													<td className="p-2">Agente {metric.agent_id}</td>
													<td className="p-2">{metric.cubes_delivered}</td>
													<td className="p-2">{metric.total_distance}m</td>
													<td className="p-2">{metric.efficiency_ratio}%</td>
													<td className="p-2">
														{metric.delivery_rate.toFixed(2)}/min
													</td>
												</tr>
											))}
										</tbody>
									</table>
								</div>
							</CardContent>
						</Card>
					</div>
				</CardContent>
			</Card>
		</div>
	);
};

export default MetricsDashboard;
