/**
 * Tests for the Comment Formatter
 */

import { describe, test, expect, beforeEach } from 'vitest';
import { CommentFormatter } from '../src/llm/comment-formatter.js';
import { PRInsights, RiskLevel } from '../src/llm/pr-context-processor.js';

describe('CommentFormatter', () => {
  let commentFormatter: CommentFormatter;
  let mockInsights: PRInsights;
  
  beforeEach(() => {
    commentFormatter = new CommentFormatter();
    
    // Create mock insights for testing
    mockInsights = {
      designDecisions: {
        summary: 'This PR implements a new feature for handling user authentication.',
        relatedADRs: [
          {
            id: 'ADR-001',
            title: 'Authentication Strategy',
            relevance: 'Defines the authentication approach used in this PR',
          },
        ],
        relatedTickets: [
          {
            id: 'ABC-123',
            title: 'Implement user authentication',
            relevance: 'This PR implements the authentication feature described in the ticket',
          },
        ],
        designPrinciples: [
          'Separation of concerns',
          'Single responsibility principle',
        ],
        explanation: 'The authentication system is designed to be modular and extensible.',
      },
      impactAnalysis: {
        summary: 'This change affects the user authentication flow.',
        riskScore: {
          score: 45,
          level: RiskLevel.MEDIUM,
          explanation: 'Medium risk due to changes in the authentication system.',
        },
        affectedComponents: [
          {
            name: 'AuthService',
            impact: 'Major changes to the authentication logic',
          },
          {
            name: 'UserController',
            impact: 'Minor changes to handle the new authentication flow',
          },
        ],
        potentialIssues: [
          'Might affect existing user sessions',
          'Could impact performance if not properly optimized',
        ],
        recommendations: [
          'Monitor authentication performance after deployment',
          'Consider adding more comprehensive tests',
        ],
      },
      testVerification: {
        summary: 'The changes are well-tested with unit and integration tests.',
        testCoverage: {
          percentage: 85,
          assessment: 'Good test coverage for the critical authentication components.',
        },
        testGaps: [
          'Missing tests for error handling edge cases',
          'No performance tests included',
        ],
        recommendations: [
          'Add tests for error handling scenarios',
          'Consider adding performance benchmarks',
        ],
      },
    };
  });
  
  test('formatComment should format the insights correctly', () => {
    const result = commentFormatter.formatComment(mockInsights, 'Implement user authentication');
    
    // Check that the result contains the expected sections
    expect(result).toContain('When reviewing this "Implement user authentication"');
    expect(result).toContain('1️⃣ The original design decisions behind the code');
    expect(result).toContain('2️⃣ The predicted impact of the change');
    expect(result).toContain('3️⃣ Proof that the change was properly tested');
    
    // Check that the result contains the design decisions
    expect(result).toContain('This PR implements a new feature for handling user authentication.');
    expect(result).toContain('Authentication Strategy');
    expect(result).toContain('Implement user authentication');
    expect(result).toContain('Separation of concerns');
    
    // Check that the result contains the impact analysis
    expect(result).toContain('This change affects the user authentication flow.');
    expect(result).toContain('Risk Score:');
    expect(result).toContain('45/100');
    expect(result).toContain('AuthService');
    expect(result).toContain('UserController');
    
    // Check that the result contains the test verification
    expect(result).toContain('The changes are well-tested with unit and integration tests.');
    expect(result).toContain('Test Coverage:');
    expect(result).toContain('85%');
    expect(result).toContain('Missing tests for error handling edge cases');
  });
  
  test('formatComment should handle missing PR title', () => {
    const result = commentFormatter.formatComment(mockInsights);
    
    // Check that the result uses a generic PR reference
    expect(result).toContain('When reviewing this PR');
  });
  
  test('formatCodeDiff should format the diff correctly', () => {
    const diff = `@@ -1,5 +1,7 @@
 const auth = require('./auth');
+const jwt = require('jsonwebtoken');
 
 function authenticate(req, res, next) {
+  const token = req.headers.authorization;
   // Implementation
 }`;
    
    const result = commentFormatter.formatCodeDiff(diff);
    
    // Check that the result contains the diff in a collapsible section
    expect(result).toContain('<details>');
    expect(result).toContain('<summary>View Code Changes</summary>');
    expect(result).toContain('```diff');
    expect(result).toContain(diff);
    expect(result).toContain('```');
    expect(result).toContain('</details>');
  });
});
