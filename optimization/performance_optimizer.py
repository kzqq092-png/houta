"""
Performance Optimization Module for Trading System
Provides performance monitoring and optimization suggestions
"""

import psutil
import time
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
import logging

class PerformanceOptimizer:
    """Performance optimization tools for trading system"""
    
    def __init__(self):
        self.metrics = {}
        self.thresholds = {
            'cpu_usage': 80,  # 80% CPU usage threshold
            'memory_usage': 85,  # 85% memory usage threshold
            'operation_time': 1.0,  # 1 second operation time threshold
            'data_load_time': 2.0  # 2 seconds data load time threshold
        }
        self.start_time = time.time()
        self.operation_times = {}
        
    def monitor_operation(self, operation: str) -> None:
        """Monitor operation execution time
        
        Args:
            operation: Name of the operation to monitor
        """
        if operation not in self.operation_times:
            self.operation_times[operation] = []
            
        self.operation_times[operation].append(time.time())
        
    def end_operation(self, operation: str) -> float:
        """End operation monitoring and get execution time
        
        Args:
            operation: Name of the operation to end
            
        Returns:
            Execution time in seconds
        """
        if operation in self.operation_times and self.operation_times[operation]:
            start_time = self.operation_times[operation].pop()
            execution_time = time.time() - start_time
            
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(execution_time)
            
            return execution_time
        return 0.0
        
    def get_system_metrics(self) -> Dict:
        """Get current system performance metrics
        
        Returns:
            Dict containing system metrics
        """
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Get network stats
            network = psutil.net_io_counters()
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'memory_available': memory.available / (1024 * 1024),  # MB
                'disk_usage': disk_percent,
                'disk_free': disk.free / (1024 * 1024 * 1024),  # GB
                'network_sent': network.bytes_sent / (1024 * 1024),  # MB
                'network_recv': network.bytes_recv / (1024 * 1024)  # MB
            }
            
        except Exception as e:
            logging.error(f"Failed to get system metrics: {str(e)}")
            return {}
            
    def get_operation_metrics(self) -> Dict:
        """Get operation performance metrics
        
        Returns:
            Dict containing operation metrics
        """
        metrics = {}
        
        for operation, times in self.metrics.items():
            if times:
                metrics[operation] = {
                    'avg_time': np.mean(times),
                    'max_time': max(times),
                    'min_time': min(times),
                    'std_time': np.std(times),
                    'count': len(times)
                }
                
        return metrics
        
    def get_optimization_suggestions(self) -> List[Dict]:
        """Generate performance optimization suggestions
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        system_metrics = self.get_system_metrics()
        operation_metrics = self.get_operation_metrics()
        
        # Check system resources
        if system_metrics.get('cpu_usage', 0) > self.thresholds['cpu_usage']:
            suggestions.append({
                'type': 'system',
                'component': 'CPU',
                'severity': 'high',
                'message': 'High CPU usage detected. Consider optimizing computationally intensive operations.',
                'suggestions': [
                    'Use caching for frequently accessed data',
                    'Implement parallel processing for heavy computations',
                    'Optimize algorithm complexity'
                ]
            })
            
        if system_metrics.get('memory_usage', 0) > self.thresholds['memory_usage']:
            suggestions.append({
                'type': 'system',
                'component': 'Memory',
                'severity': 'high',
                'message': 'High memory usage detected. Consider implementing memory optimization.',
                'suggestions': [
                    'Implement data streaming for large datasets',
                    'Clear unused cache periodically',
                    'Optimize object lifecycle management'
                ]
            })
            
        # Check operation performance
        for operation, metrics in operation_metrics.items():
            if metrics['avg_time'] > self.thresholds['operation_time']:
                suggestions.append({
                    'type': 'operation',
                    'component': operation,
                    'severity': 'medium',
                    'message': f'Slow operation detected: {operation}',
                    'suggestions': [
                        'Implement caching mechanism',
                        'Optimize algorithm efficiency',
                        'Consider parallel processing'
                    ]
                })
                
        # Check data loading performance
        data_operations = [op for op in operation_metrics.keys() if 'data' in op.lower()]
        for operation in data_operations:
            metrics = operation_metrics[operation]
            if metrics['avg_time'] > self.thresholds['data_load_time']:
                suggestions.append({
                    'type': 'data',
                    'component': operation,
                    'severity': 'medium',
                    'message': f'Slow data loading detected: {operation}',
                    'suggestions': [
                        'Implement data prefetching',
                        'Use data compression',
                        'Optimize database queries',
                        'Consider data partitioning'
                    ]
                })
                
        return suggestions
        
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report
        
        Returns:
            Dict containing performance report
        """
        return {
            'system_metrics': self.get_system_metrics(),
            'operation_metrics': self.get_operation_metrics(),
            'optimization_suggestions': self.get_optimization_suggestions(),
            'uptime': time.time() - self.start_time
        }
        
    def reset_metrics(self) -> None:
        """Reset all performance metrics"""
        self.metrics = {}
        self.operation_times = {}
        self.start_time = time.time()
        
    def set_threshold(self, metric: str, value: float) -> None:
        """Set performance threshold for a metric
        
        Args:
            metric: Name of the metric
            value: Threshold value
        """
        self.thresholds[metric] = value
        
    def get_threshold(self, metric: str) -> Optional[float]:
        """Get performance threshold for a metric
        
        Args:
            metric: Name of the metric
            
        Returns:
            Threshold value if exists, None otherwise
        """
        return self.thresholds.get(metric) 