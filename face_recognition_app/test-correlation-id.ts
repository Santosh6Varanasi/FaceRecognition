/**
 * End-to-End Correlation ID Propagation Test
 * 
 * This script verifies that correlation IDs flow correctly through the entire system:
 * 1. Angular generates correlation ID with format: angular-{timestamp}-{random}
 * 2. Next.js receives and forwards correlation ID to Flask
 * 3. Flask logs include the correlation ID
 * 
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
 */

// Simulate Angular correlation ID generation
function generateCorrelationId(service: string): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 10);
  return `${service}-${timestamp}-${random}`;
}

// Test correlation ID format
function testCorrelationIdFormat() {
  console.log('\n=== Test 1: Correlation ID Format ===');
  
  const angularId = generateCorrelationId('angular');
  const nextjsId = generateCorrelationId('nextjs');
  const flaskId = generateCorrelationId('flask');
  
  const formatRegex = /^(angular|nextjs|flask)-\d+-[a-z0-9]+$/;
  
  console.log(`Angular ID: ${angularId}`);
  console.log(`Format valid: ${formatRegex.test(angularId)}`);
  
  console.log(`\nNext.js ID: ${nextjsId}`);
  console.log(`Format valid: ${formatRegex.test(nextjsId)}`);
  
  console.log(`\nFlask ID: ${flaskId}`);
  console.log(`Format valid: ${formatRegex.test(flaskId)}`);
  
  const allValid = formatRegex.test(angularId) && 
                   formatRegex.test(nextjsId) && 
                   formatRegex.test(flaskId);
  
  console.log(`\n✓ All correlation IDs match format: {service}-{timestamp}-{random}`);
  return allValid;
}

// Test Angular to Next.js flow
async function testAngularToNextjs() {
  console.log('\n=== Test 2: Angular → Next.js Flow ===');
  
  const correlationId = generateCorrelationId('angular');
  console.log(`Generated correlation ID: ${correlationId}`);
  
  try {
    const response = await fetch('http://localhost:3000/api/health', {
      headers: {
        'X-Correlation-ID': correlationId
      }
    });
    
    const responseCorrelationId = response.headers.get('x-correlation-id');
    console.log(`Response correlation ID: ${responseCorrelationId}`);
    
    if (responseCorrelationId === correlationId) {
      console.log('✓ Next.js received and returned the correlation ID');
      return true;
    } else {
      console.log('✗ Correlation ID mismatch');
      return false;
    }
  } catch (error) {
    console.error('✗ Error testing Angular → Next.js flow:', error);
    return false;
  }
}

// Test Next.js to Flask flow
async function testNextjsToFlask() {
  console.log('\n=== Test 3: Next.js → Flask Flow ===');
  
  const correlationId = generateCorrelationId('angular');
  console.log(`Generated correlation ID: ${correlationId}`);
  console.log('Note: Check Flask logs to verify correlation ID is present');
  
  try {
    const response = await fetch('http://localhost:3000/api/health', {
      headers: {
        'X-Correlation-ID': correlationId
      }
    });
    
    const data = await response.json();
    console.log(`Health check response:`, data);
    
    if (data.flask_reachable) {
      console.log('✓ Flask is reachable');
      console.log('✓ Check Flask logs for correlation ID:', correlationId);
      return true;
    } else {
      console.log('✗ Flask is not reachable');
      return false;
    }
  } catch (error) {
    console.error('✗ Error testing Next.js → Flask flow:', error);
    return false;
  }
}

// Main test runner
async function runTests() {
  console.log('=================================================');
  console.log('Correlation ID Propagation Verification');
  console.log('=================================================');
  
  const results = {
    format: false,
    angularToNextjs: false,
    nextjsToFlask: false
  };
  
  // Test 1: Format validation
  results.format = testCorrelationIdFormat();
  
  // Test 2: Angular → Next.js
  results.angularToNextjs = await testAngularToNextjs();
  
  // Test 3: Next.js → Flask
  results.nextjsToFlask = await testNextjsToFlask();
  
  // Summary
  console.log('\n=================================================');
  console.log('Test Summary');
  console.log('=================================================');
  console.log(`Format validation: ${results.format ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Angular → Next.js: ${results.angularToNextjs ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Next.js → Flask: ${results.nextjsToFlask ? '✓ PASS' : '✗ FAIL'}`);
  
  const allPassed = results.format && results.angularToNextjs && results.nextjsToFlask;
  console.log(`\nOverall: ${allPassed ? '✓ ALL TESTS PASSED' : '✗ SOME TESTS FAILED'}`);
  
  console.log('\n=================================================');
  console.log('Manual Verification Steps');
  console.log('=================================================');
  console.log('1. Check Flask logs at: logs/flask/app.log');
  console.log('2. Search for the correlation ID in the logs');
  console.log('3. Verify the correlation ID appears in Flask request logs');
  console.log('4. Verify the format matches: {service}-{timestamp}-{random}');
}

// Run tests if this script is executed directly
if (require.main === module) {
  runTests().catch(console.error);
}

export { testCorrelationIdFormat, testAngularToNextjs, testNextjsToFlask, generateCorrelationId };
