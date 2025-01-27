self.onmessage = function (event) {
    const { data, filters } = event.data;
    let filteredData = data.slice();
  
    // Apply filters
    if (filters.userId) {
      filteredData = filteredData.filter(item => item.user_id === filters.userId);
    }
    if (filters.queryType) {
      filteredData = filteredData.filter(item => item.query_type === filters.queryType);
    }
  
    // Perform calculations
    const kpis = calculateKPIs(filteredData);
    const executionTimeData = calculateExecutionTimeData(filteredData);
    const stableQueryData = calculateStableQueryData(filteredData);
    const throughputData = calculateThroughputData(filteredData);
    const failuresData = calculateFailuresData(filteredData);
  
    // Send results back to the main thread
    self.postMessage({ kpis, executionTimeData, stableQueryData, throughputData, failuresData });
  };
  
  // Calculate KPIs (Key Performance Indicators)
  function calculateKPIs(data) {
    const totalQueries = data.reduce((sum, item) => sum + (parseInt(item.query_count) || 0), 0);
    const stableQueries = data.filter(item => item.short_fingerprint !== 'Unknown').length;
    const abortedQueries = data.reduce((sum, item) => {
      const failCount = parseInt(item.failure_count, 10);
      return sum + (isNaN(failCount) ? 0 : failCount);
    }, 0);
    return { totalQueries, stableQueries, abortedQueries };
  }
  
  // Calculate execution time data (grouped by day)
  function calculateExecutionTimeData(data) {
    const validData = data.filter(
      item =>
        item.short_fingerprint !== 'Unknown' &&
        !isNaN(parseFloat(item.avg_execution_time)) &&
        item.arrival_timestamp
    );
  
    if (validData.length === 0) return [];
  
    // Group by day and calculate average execution time
    const dailyData = validData.reduce((acc, item) => {
      const dateStr = new Date(item.arrival_timestamp).toISOString().split('T')[0]; // YYYY-MM-DD
      if (!acc[dateStr]) acc[dateStr] = { total: 0, count: 0 };
      acc[dateStr].total += parseFloat(item.avg_execution_time);
      acc[dateStr].count += 1;
      return acc;
    }, {});
  
    const labels = Object.keys(dailyData).sort();
    const avgTimes = labels.map(date => {
      const obj = dailyData[date];
      return (obj.total / obj.count).toFixed(2);
    });
  
    return validData; // Ensure an array is returned
  }
  
  // Calculate stable query performance data
  function calculateStableQueryData(data) {
    const stableData = data.filter(item => item.short_fingerprint !== 'Unknown');
  
    if (stableData.length === 0) return [];
  
    const labels = stableData.map(item => item.short_fingerprint);
    const executionTimes = stableData.map(item => parseFloat(item.avg_execution_time) || 0);
  
    return { labels, executionTimes };
  }
  
  // Calculate query throughput data (grouped by hour)
  function calculateThroughputData(data) {
    const throughputByHour = data.reduce((acc, item) => {
      let timestamp = item.arrival_timestamp;
      if (timestamp) {
        try {
          timestamp = timestamp.split('.')[0]; // Remove microseconds if present
          const dateObj = new Date(timestamp);
          if (!isNaN(dateObj.getTime())) {
            // Hour as 'YYYY-MM-DDTHH'
            const hourStr = dateObj.toISOString().slice(0, 13);
            acc[hourStr] = (acc[hourStr] || 0) + 1;
          }
        } catch (e) {
          console.warn("Error parsing timestamp:", timestamp, e);
        }
      }
      return acc;
    }, {});
  
    const labels = Object.keys(throughputByHour).sort();
    const throughput = labels.map(label => throughputByHour[label]);
  
    return { labels, throughput };
  }
  
  // Calculate query failures data
  function calculateFailuresData(data) {
    const failedData = data.filter(item => parseInt(item.failure_count) > 0);
  
    if (failedData.length === 0) return [];
  
    const labels = failedData.map(item => item.short_fingerprint);
    const failureCounts = failedData.map(item => parseInt(item.failure_count));
  
    return { labels, failureCounts };
  }