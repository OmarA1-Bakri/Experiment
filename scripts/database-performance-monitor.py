#!/usr/bin/env python3
"""
Database Performance Monitoring Script
Monitors PostgreSQL database performance and identifies optimization opportunities
"""

import psycopg2
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabasePerformanceMonitor:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'database_metrics': {},
            'slow_queries': [],
            'index_recommendations': [],
            'performance_issues': [],
            'optimization_suggestions': []
        }

    def connect(self):
        """Establish database connection"""
        try:
            return psycopg2.connect(self.connection_string)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_database_metrics(self) -> Dict[str, Any]:
        """Collect basic database metrics"""
        metrics = {}
        
        queries = {
            'database_size': """
                SELECT pg_database_size(current_database()) as size_bytes,
                       pg_size_pretty(pg_database_size(current_database())) as size_human
            """,
            'table_sizes': """
                SELECT schemaname, tablename, 
                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """,
            'connection_stats': """
                SELECT count(*) as total_connections,
                       count(*) FILTER (WHERE state = 'active') as active_connections,
                       count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """,
            'cache_hit_ratio': """
                SELECT 
                    CASE 
                        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
                        ELSE sum(heap_blks_hit)::float / (sum(heap_blks_hit) + sum(heap_blks_read))
                    END as ratio
                FROM pg_statio_user_tables
            """
        }

        with self.connect() as conn:
            with conn.cursor() as cursor:
                for metric_name, query in queries.items():
                    try:
                        cursor.execute(query)
                        result = cursor.fetchall()
                        metrics[metric_name] = result
                    except Exception as e:
                        logger.error(f"Error collecting {metric_name}: {e}")
                        metrics[metric_name] = []

        return metrics

    def get_table_statistics(self) -> List[Dict[str, Any]]:
        """Get detailed table statistics"""
        table_stats = []
        
        query = """
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
        """

        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    for row in cursor.fetchall():
                        table_stats.append(dict(zip(columns, row)))
        except Exception as e:
            logger.error(f"Error collecting table statistics: {e}")

        return table_stats

    def get_index_analysis(self) -> List[Dict[str, Any]]:
        """Analyze index usage and effectiveness"""
        index_analysis = []
        
        query = """
            SELECT 
                schemaname,
                tablename,
                indexrelname as index_name,
                idx_scan as index_scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                CASE 
                    WHEN idx_scan = 0 THEN 'Unused'
                    WHEN idx_tup_fetch::float / idx_tup_read < 0.1 THEN 'Inefficient'
                    ELSE 'Efficient'
                END as efficiency
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
        """

        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    for row in cursor.fetchall():
                        index_analysis.append(dict(zip(columns, row)))
        except Exception as e:
            logger.error(f"Error analyzing indexes: {e}")

        return index_analysis

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        logger.info("Starting database performance analysis...")
        
        try:
            # Collect all metrics
            self.results['database_metrics'] = self.get_database_metrics()
            self.results['table_statistics'] = self.get_table_statistics()
            self.results['index_analysis'] = self.get_index_analysis()
            
            # Generate recommendations
            self.generate_recommendations()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return self.results

    def generate_recommendations(self):
        """Generate optimization recommendations based on collected data"""
        recommendations = []
        
        # Check for large tables without indexes
        if 'table_statistics' in self.results:
            for table in self.results['table_statistics']:
                if table['live_tuples'] > 10000:  # Large tables
                    recommendations.append({
                        'type': 'index_needed',
                        'table': table['tablename'],
                        'reason': f"Large table ({table['live_tuples']} rows) may benefit from indexes",
                        'priority': 'medium'
                    })
        
        # Check for high dead tuple ratio
        for table in self.results.get('table_statistics', []):
            if table['live_tuples'] > 0:
                dead_ratio = table['dead_tuples'] / table['live_tuples']
                if dead_ratio > 0.2:  # 20% dead tuples
                    recommendations.append({
                        'type': 'vacuum_needed',
                        'table': table['tablename'],
                        'reason': f"High dead tuple ratio ({dead_ratio:.2%}) - consider VACUUM",
                        'priority': 'low'
                    })
        
        # Check for unused indexes
        for index in self.results.get('index_analysis', []):
            if index['efficiency'] == 'Unused':
                recommendations.append({
                    'type': 'unused_index',
                    'index': index['index_name'],
                    'table': index['tablename'],
                    'reason': "Index is never used - consider removal",
                    'priority': 'low'
                })
        
        self.results['optimization_suggestions'] = recommendations

    def save_report(self, filename: str = None):
        """Save performance report to file"""
        if filename is None:
            filename = f"database-performance-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"Performance report saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")

def main():
    """Main execution function"""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/ruleiq')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return
    
    monitor = DatabasePerformanceMonitor(database_url)
    
    try:
        report = monitor.generate_performance_report()
        monitor.save_report()
        
        # Print summary
        print("\n📊 Database Performance Summary")
        print("=" * 40)
        
        if 'database_metrics' in report and report['database_metrics'].get('database_size'):
            size_info = report['database_metrics']['database_size'][0]
            print(f"Database Size: {size_info[1]}")
        
        if 'table_statistics' in report:
            print(f"Total Tables: {len(report['table_statistics'])}")
            large_tables = [t for t in report['table_statistics'] if t['live_tuples'] > 10000]
            print(f"Large Tables (>10k rows): {len(large_tables)}")
        
        if 'optimization_suggestions' in report:
            print(f"Optimization Suggestions: {len(report['optimization_suggestions'])}")
            for suggestion in report['optimization_suggestions'][:3]:
                print(f"  - {suggestion['type']}: {suggestion.get('table', suggestion.get('index', 'N/A'))}")
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        logger.error(f"Failed to run performance analysis: {e}")

if __name__ == "__main__":
    main()