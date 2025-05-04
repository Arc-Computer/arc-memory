import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ContextGenerator } from '../src/context-generator';
import { GraphService, NodeType, EdgeRel } from '../src/graph-service';

// Mock the GraphService
vi.mock('../src/graph-service', () => {
  const GraphService = vi.fn().mockImplementation(() => {
    return {
      connect: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
      findLinearTicketsForPR: vi.fn().mockResolvedValue([]),
      findADRsForChangedFiles: vi.fn().mockResolvedValue([]),
      getCommitHistoryForPR: vi.fn().mockResolvedValue([]),
      findRelatedPRsForFile: vi.fn().mockResolvedValue([]),
      searchNodes: vi.fn().mockResolvedValue([]),
    };
  });
  
  // Keep the enums
  return {
    GraphService,
    NodeType: {
      COMMIT: 'commit',
      FILE: 'file',
      PR: 'pr',
      ISSUE: 'issue',
      ADR: 'adr',
    },
    EdgeRel: {
      MODIFIES: 'MODIFIES',
      MERGES: 'MERGES',
      MENTIONS: 'MENTIONS',
      DECIDES: 'DECIDES',
    },
  };
});

describe('ContextGenerator', () => {
  let contextGenerator: ContextGenerator;
  let mockGraphService: any;
  let mockContext: any;
  
  beforeEach(() => {
    mockGraphService = new GraphService();
    contextGenerator = new ContextGenerator(mockGraphService);
    
    // Mock the Probot context
    mockContext = {
      payload: {
        pull_request: {
          number: 123,
          title: 'Test PR',
          body: 'This is a test PR that fixes ABC-123',
          user: {
            login: 'test-user',
          },
          base: {
            ref: 'main',
          },
          head: {
            ref: 'feature/ABC-123-test',
          },
        },
        repository: {
          name: 'test-repo',
          owner: {
            login: 'test-owner',
          },
        },
      },
      octokit: {
        pulls: {
          listFiles: vi.fn().mockResolvedValue({
            data: [
              {
                filename: 'test-file.ts',
                status: 'modified',
                additions: 10,
                deletions: 5,
                changes: 15,
                patch: '@@ -1,5 +1,10 @@',
              },
            ],
          }),
        },
      },
      issue: vi.fn().mockImplementation((params) => params),
    };
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });
  
  it('should generate context for a PR', async () => {
    // Mock the GraphService responses
    mockGraphService.findLinearTicketsForPR.mockResolvedValue([
      {
        id: 'issue:ABC-123',
        type: NodeType.ISSUE,
        title: 'Test Linear Ticket',
        body: 'This is a test Linear ticket',
        number: 123,
        state: 'In Progress',
        url: 'https://linear.app/test/issue/ABC-123',
      },
    ]);
    
    mockGraphService.findADRsForChangedFiles.mockResolvedValue([
      {
        id: 'adr:test-adr',
        type: NodeType.ADR,
        title: 'Test ADR',
        body: 'This is a test ADR',
        status: 'accepted',
        path: 'docs/adr/test-adr.md',
        decision_makers: ['test-user'],
      },
    ]);
    
    mockGraphService.getCommitHistoryForPR.mockResolvedValue([
      {
        id: 'commit:test-commit',
        type: NodeType.COMMIT,
        title: 'Test Commit',
        body: 'This is a test commit',
        author: 'test-user',
        sha: 'abc123',
        files: ['test-file.ts'],
      },
    ]);
    
    mockGraphService.findRelatedPRsForFile.mockResolvedValue([
      {
        id: 'pr:test-owner/test-repo#456',
        type: NodeType.PR,
        title: 'Related PR',
        body: 'This is a related PR',
        number: 456,
        state: 'merged',
        url: 'https://github.com/test-owner/test-repo/pull/456',
      },
    ]);
    
    // Call the method
    const prContext = await contextGenerator.generateContext(mockContext);
    
    // Verify the result
    expect(prContext).toBeDefined();
    expect(prContext.prNumber).toBe(123);
    expect(prContext.prTitle).toBe('Test PR');
    expect(prContext.prBody).toBe('This is a test PR that fixes ABC-123');
    expect(prContext.prAuthor).toBe('test-user');
    expect(prContext.baseRef).toBe('main');
    expect(prContext.headRef).toBe('feature/ABC-123-test');
    expect(prContext.repository).toBe('test-repo');
    expect(prContext.owner).toBe('test-owner');
    
    // Verify the changed files
    expect(prContext.changedFiles).toHaveLength(1);
    expect(prContext.changedFiles[0].filename).toBe('test-file.ts');
    
    // Verify the related entities
    expect(prContext.relatedEntities.linearTickets).toHaveLength(1);
    expect(prContext.relatedEntities.linearTickets[0].title).toBe('Test Linear Ticket');
    
    expect(prContext.relatedEntities.adrs).toHaveLength(1);
    expect(prContext.relatedEntities.adrs[0].title).toBe('Test ADR');
    
    expect(prContext.relatedEntities.commits).toHaveLength(1);
    expect(prContext.relatedEntities.commits[0].title).toBe('Test Commit');
    
    expect(prContext.relatedEntities.relatedPRs).toHaveLength(1);
    expect(prContext.relatedEntities.relatedPRs[0].title).toBe('Related PR');
    
    // Verify the GraphService methods were called
    expect(mockGraphService.findLinearTicketsForPR).toHaveBeenCalledWith(123, 'test-owner', 'test-repo');
    expect(mockGraphService.findADRsForChangedFiles).toHaveBeenCalledWith(['test-file.ts']);
    expect(mockGraphService.getCommitHistoryForPR).toHaveBeenCalledWith(123, 'test-owner', 'test-repo');
    expect(mockGraphService.findRelatedPRsForFile).toHaveBeenCalledWith('test-file.ts');
  });
});
