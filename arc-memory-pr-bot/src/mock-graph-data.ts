import { NodeType, EdgeRel, Node, Edge, LinearTicket, ADR, PR, Commit, File } from './graph-service.js';

/**
 * Mock data provider for testing the GraphService
 */
export class MockGraphData {
  nodes: Map<string, Node>;
  edges: Edge[];

  constructor() {
    this.nodes = new Map<string, Node>();
    this.edges = [];
    this.initializeMockData();
  }

  /**
   * Initialize mock data for testing
   */
  private initializeMockData(): void {
    // Initialize mock nodes representing entities like PRs and Linear Tickets
    this.createMockNodes();

    // Initialize mock edges to define relationships between nodes (e.g., PRs linked to Linear Tickets)
    this.createMockEdges();
  }

  /**
   * Create mock nodes for testing
   */
  private createMockNodes(): void {
    // Create mock PR nodes
    const pr1: PR = {
      id: 'pr:Arc-Computer/arc-memory#1',
      type: NodeType.PR,
      title: 'Add Linear OAuth integration',
      body: 'This PR implements the Linear OAuth 2.0 flow as described in the Linear API documentation.',
      number: 1,
      state: 'merged',
      url: 'https://github.com/Arc-Computer/arc-memory/pull/1',
      merged_at: '2023-05-01T12:00:00Z',
      merged_by: 'test-user',
      extra: {
        number: 1,
        state: 'merged',
        url: 'https://github.com/Arc-Computer/arc-memory/pull/1',
        merged_at: '2023-05-01T12:00:00Z',
        merged_by: 'test-user',
      },
    };

    const pr2: PR = {
      id: 'pr:Arc-Computer/arc-memory#2',
      type: NodeType.PR,
      title: 'Implement GitHub PR Bot',
      body: 'This PR implements the GitHub PR Bot that enhances pull requests with contextual information from the knowledge graph.',
      number: 2,
      state: 'open',
      url: 'https://github.com/Arc-Computer/arc-memory/pull/2',
      extra: {
        number: 2,
        state: 'open',
        url: 'https://github.com/Arc-Computer/arc-memory/pull/2',
      },
    };

    // Create mock Linear ticket nodes
    const linearTicket1: LinearTicket = {
      id: 'issue:linear/ARC-42',
      type: NodeType.ISSUE,
      title: 'Implement Linear OAuth flow',
      body: 'Implement the Linear OAuth 2.0 flow as described in the Linear API documentation.',
      number: 42,
      state: 'completed',
      url: 'https://linear.app/arc-computer/issue/ARC-42',
      extra: {
        number: 42,
        state: 'completed',
        url: 'https://linear.app/arc-computer/issue/ARC-42',
      },
    };

    const linearTicket2: LinearTicket = {
      id: 'issue:linear/ARC-43',
      type: NodeType.ISSUE,
      title: 'Implement GitHub PR Bot',
      body: 'Create a GitHub PR Bot that enhances pull requests with contextual information from the knowledge graph.',
      number: 43,
      state: 'in-progress',
      url: 'https://linear.app/arc-computer/issue/ARC-43',
      extra: {
        number: 43,
        state: 'in-progress',
        url: 'https://linear.app/arc-computer/issue/ARC-43',
      },
    };

    // Create mock ADR nodes
    const adr1: ADR = {
      id: 'adr:arc-memory/adr-001',
      type: NodeType.ADR,
      title: 'Use SQLite for Knowledge Graph Storage',
      body: 'We will use SQLite for storing the knowledge graph because it is lightweight, portable, and supports the features we need.',
      status: 'accepted',
      path: 'docs/adr/adr-001-sqlite-storage.md',
      decision_makers: ['test-user'],
      extra: {
        status: 'accepted',
        path: 'docs/adr/adr-001-sqlite-storage.md',
        decision_makers: ['test-user'],
      },
    };

    const adr2: ADR = {
      id: 'adr:arc-memory/adr-005',
      type: NodeType.ADR,
      title: 'Authentication Mechanisms',
      body: 'We will use OAuth 2.0 for authentication with GitHub and Linear to improve security and user experience.',
      status: 'accepted',
      path: 'docs/adr/adr-005-authentication.md',
      decision_makers: ['test-user'],
      extra: {
        status: 'accepted',
        path: 'docs/adr/adr-005-authentication.md',
        decision_makers: ['test-user'],
      },
    };

    // Create mock commit nodes
    const commit1: Commit = {
      id: 'commit:abc123',
      type: NodeType.COMMIT,
      title: 'Add Linear OAuth implementation',
      body: 'This commit adds the Linear OAuth 2.0 implementation.',
      author: 'test-user',
      sha: 'abc123',
      files: ['arc_memory/auth/linear.py', 'arc_memory/cli/auth.py'],
      extra: {
        author: 'test-user',
        sha: 'abc123',
        files: ['arc_memory/auth/linear.py', 'arc_memory/cli/auth.py'],
        timestamp: '2023-05-01T10:00:00Z',
      },
    };

    const commit2: Commit = {
      id: 'commit:def456',
      type: NodeType.COMMIT,
      title: 'Add GitHub PR Bot implementation',
      body: 'This commit adds the GitHub PR Bot implementation.',
      author: 'test-user',
      sha: 'def456',
      files: ['pr-bot/src/index.ts', 'pr-bot/src/graph-service.ts'],
      extra: {
        author: 'test-user',
        sha: 'def456',
        files: ['pr-bot/src/index.ts', 'pr-bot/src/graph-service.ts'],
        timestamp: '2023-05-02T10:00:00Z',
      },
    };

    // Create mock file nodes
    const file1: File = {
      id: 'file:arc_memory/auth/linear.py',
      type: NodeType.FILE,
      title: 'arc_memory/auth/linear.py',
      body: null,
      path: 'arc_memory/auth/linear.py',
      language: 'python',
      extra: {
        path: 'arc_memory/auth/linear.py',
        language: 'python',
        last_modified: '2023-05-01T10:00:00Z',
      },
    };

    const file2: File = {
      id: 'file:arc_memory/cli/auth.py',
      type: NodeType.FILE,
      title: 'arc_memory/cli/auth.py',
      body: null,
      path: 'arc_memory/cli/auth.py',
      language: 'python',
      extra: {
        path: 'arc_memory/cli/auth.py',
        language: 'python',
        last_modified: '2023-05-01T10:00:00Z',
      },
    };

    const file3: File = {
      id: 'file:pr-bot/src/index.ts',
      type: NodeType.FILE,
      title: 'pr-bot/src/index.ts',
      body: null,
      path: 'pr-bot/src/index.ts',
      language: 'typescript',
      extra: {
        path: 'pr-bot/src/index.ts',
        language: 'typescript',
        last_modified: '2023-05-02T10:00:00Z',
      },
    };

    const file4: File = {
      id: 'file:pr-bot/src/graph-service.ts',
      type: NodeType.FILE,
      title: 'pr-bot/src/graph-service.ts',
      body: null,
      path: 'pr-bot/src/graph-service.ts',
      language: 'typescript',
      extra: {
        path: 'pr-bot/src/graph-service.ts',
        language: 'typescript',
        last_modified: '2023-05-02T10:00:00Z',
      },
    };

    // Add all nodes to the map
    this.nodes.set(pr1.id, pr1);
    this.nodes.set(pr2.id, pr2);
    this.nodes.set(linearTicket1.id, linearTicket1);
    this.nodes.set(linearTicket2.id, linearTicket2);
    this.nodes.set(adr1.id, adr1);
    this.nodes.set(adr2.id, adr2);
    this.nodes.set(commit1.id, commit1);
    this.nodes.set(commit2.id, commit2);
    this.nodes.set(file1.id, file1);
    this.nodes.set(file2.id, file2);
    this.nodes.set(file3.id, file3);
    this.nodes.set(file4.id, file4);
  }

  /**
   * Create mock edges for testing
   */
  private createMockEdges(): void {
    // PR1 mentions Linear ticket 1
    this.edges.push({
      src: 'pr:Arc-Computer/arc-memory#1',
      dst: 'issue:linear/ARC-42',
      rel: EdgeRel.MENTIONS,
      properties: {},
    });

    // PR2 mentions Linear ticket 2
    this.edges.push({
      src: 'pr:Arc-Computer/arc-memory#2',
      dst: 'issue:linear/ARC-43',
      rel: EdgeRel.MENTIONS,
      properties: {},
    });

    // PR1 merges commit1
    this.edges.push({
      src: 'pr:Arc-Computer/arc-memory#1',
      dst: 'commit:abc123',
      rel: EdgeRel.MERGES,
      properties: {},
    });

    // PR2 merges commit2
    this.edges.push({
      src: 'pr:Arc-Computer/arc-memory#2',
      dst: 'commit:def456',
      rel: EdgeRel.MERGES,
      properties: {},
    });

    // commit1 modifies file1 and file2
    this.edges.push({
      src: 'commit:abc123',
      dst: 'file:arc_memory/auth/linear.py',
      rel: EdgeRel.MODIFIES,
      properties: {},
    });
    this.edges.push({
      src: 'commit:abc123',
      dst: 'file:arc_memory/cli/auth.py',
      rel: EdgeRel.MODIFIES,
      properties: {},
    });

    // commit2 modifies file3 and file4
    this.edges.push({
      src: 'commit:def456',
      dst: 'file:pr-bot/src/index.ts',
      rel: EdgeRel.MODIFIES,
      properties: {},
    });
    this.edges.push({
      src: 'commit:def456',
      dst: 'file:pr-bot/src/graph-service.ts',
      rel: EdgeRel.MODIFIES,
      properties: {},
    });

    // ADR1 decides on file1
    this.edges.push({
      src: 'adr:arc-memory/adr-001',
      dst: 'file:arc_memory/auth/linear.py',
      rel: EdgeRel.DECIDES,
      properties: {},
    });

    // ADR2 decides on file1 and file2
    this.edges.push({
      src: 'adr:arc-memory/adr-005',
      dst: 'file:arc_memory/auth/linear.py',
      rel: EdgeRel.DECIDES,
      properties: {},
    });
    this.edges.push({
      src: 'adr:arc-memory/adr-005',
      dst: 'file:arc_memory/cli/auth.py',
      rel: EdgeRel.DECIDES,
      properties: {},
    });
  }

  /**
   * Get a node by its ID
   * @param id The ID of the node to retrieve
   * @returns The node, or null if not found
   */
  getNodeById(id: string): Node | null {
    return this.nodes.get(id) || null;
  }

  /**
   * Get edges by source node ID
   * @param srcId The ID of the source node
   * @param relType Optional relationship type to filter by
   * @returns An array of edges
   */
  getEdgesBySrc(srcId: string, relType?: EdgeRel): Edge[] {
    return this.edges.filter(edge =>
      edge.src === srcId && (relType === undefined || edge.rel === relType)
    );
  }

  /**
   * Get edges by destination node ID
   * @param dstId The ID of the destination node
   * @param relType Optional relationship type to filter by
   * @returns An array of edges
   */
  getEdgesByDst(dstId: string, relType?: EdgeRel): Edge[] {
    return this.edges.filter(edge =>
      edge.dst === dstId && (relType === undefined || edge.rel === relType)
    );
  }
}
