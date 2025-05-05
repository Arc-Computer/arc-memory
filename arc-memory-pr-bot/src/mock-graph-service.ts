import { Logger } from 'probot';
import {
  GraphService,
  EdgeRel,
  Node,
  Edge,
  LinearTicket,
  ADR,
  PR,
  Commit
} from './graph-service.js';
import { MockGraphData } from './mock-graph-data.js';

/**
 * Mock implementation of the GraphService for testing
 */
export class MockGraphService extends GraphService {
  private mockData: MockGraphData;
  private connected: boolean = false;

  /**
   * Create a new MockGraphService instance
   * @param logger Logger instance
   */
  constructor(logger: Logger) {
    super(logger, 'mock-db-path');
    this.mockData = new MockGraphData();
  }

  /**
   * Connect to the mock database
   * @returns A promise that resolves when the connection is established
   */
  async connect(): Promise<void> {
    this.connected = true;
    return Promise.resolve();
  }

  /**
   * Close the mock database connection
   * @returns A promise that resolves when the connection is closed
   */
  async close(): Promise<void> {
    this.connected = false;
    return Promise.resolve();
  }

  /**
   * Check if the mock database connection is open
   * @returns True if the connection is open, false otherwise
   */
  isConnected(): boolean {
    return this.connected;
  }

  // Note: We're not overriding ensureConnected here because it's private in the parent class
  // Instead, we're relying on our own isConnected() implementation

  /**
   * Get a node by its ID from the mock data
   * @param id The ID of the node to retrieve
   * @returns The node, or null if not found
   */
  async getNodeById(id: string): Promise<Node | null> {
    this.ensureConnected();
    return Promise.resolve(this.mockData.getNodeById(id));
  }

  /**
   * Get edges by source node ID from the mock data
   * @param srcId The ID of the source node
   * @param relType Optional relationship type to filter by
   * @returns An array of edges
   */
  async getEdgesBySrc(srcId: string, relType?: EdgeRel): Promise<Edge[]> {
    this.ensureConnected();
    return Promise.resolve(this.mockData.getEdgesBySrc(srcId, relType));
  }

  /**
   * Get edges by destination node ID from the mock data
   * @param dstId The ID of the destination node
   * @param relType Optional relationship type to filter by
   * @returns An array of edges
   */
  async getEdgesByDst(dstId: string, relType?: EdgeRel): Promise<Edge[]> {
    this.ensureConnected();
    return Promise.resolve(this.mockData.getEdgesByDst(dstId, relType));
  }

  /**
   * Find Linear tickets related to a PR/branch from the mock data
   * @param prNumber The PR number
   * @param owner The repository owner
   * @param repo The repository name
   * @returns An array of Linear tickets
   */
  async findLinearTicketsForPR(prNumber: number, owner: string, repo: string): Promise<LinearTicket[]> {
    this.ensureConnected();

    // Use the parent class implementation, which will call our mocked methods
    return super.findLinearTicketsForPR(prNumber, owner, repo);
  }

  /**
   * Retrieve ADRs related to changed files from the mock data
   * @param changedFiles Array of file paths that were changed
   * @returns An array of ADRs
   */
  async findADRsForChangedFiles(changedFiles: string[]): Promise<ADR[]> {
    this.ensureConnected();

    // Use the parent class implementation, which will call our mocked methods
    return super.findADRsForChangedFiles(changedFiles);
  }

  /**
   * Extract commit history and context for a PR from the mock data
   * @param prNumber The PR number
   * @param owner The repository owner
   * @param repo The repository name
   * @returns An array of commits
   */
  async getCommitHistoryForPR(prNumber: number, owner: string, repo: string): Promise<Commit[]> {
    this.ensureConnected();

    // Use the parent class implementation, which will call our mocked methods
    return super.getCommitHistoryForPR(prNumber, owner, repo);
  }

  /**
   * Find related PRs for a file from the mock data
   * @param filePath The file path
   * @returns An array of PRs
   */
  async findRelatedPRsForFile(filePath: string): Promise<PR[]> {
    this.ensureConnected();

    // Use the parent class implementation, which will call our mocked methods
    return super.findRelatedPRsForFile(filePath);
  }

  /**
   * Get the mock database statistics
   * @returns An object with node and edge counts
   */
  async getStats(): Promise<{ nodeCount: number; edgeCount: number }> {
    this.ensureConnected();

    return Promise.resolve({
      nodeCount: this.mockData.nodes.size,
      edgeCount: this.mockData.edges.length,
    });
  }
}
