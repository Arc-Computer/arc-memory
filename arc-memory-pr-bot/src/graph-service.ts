
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import NodeCache from 'node-cache';
import { Logger } from 'probot';
import { open, Database } from 'sqlite';
import * as sqlite3 from 'sqlite3';


/**
 * Node types in the knowledge graph
 */
export enum NodeType {
  COMMIT = 'commit',
  FILE = 'file',
  PR = 'pr',
  ISSUE = 'issue',
  ADR = 'adr',
}

/**
 * Edge relationship types in the knowledge graph
 */
export enum EdgeRel {
  MODIFIES = 'MODIFIES', // Commit modifies a file
  MERGES = 'MERGES',     // PR merges a commit
  MENTIONS = 'MENTIONS', // PR/Issue mentions another entity
  DECIDES = 'DECIDES',   // ADR decides on a file/commit
}

/**
 * Node interface representing a node in the knowledge graph
 */
export interface Node {
  id: string;
  type: NodeType;
  title: string | null;
  body: string | null;
  extra: Record<string, any>;
}

/**
 * Edge interface representing an edge in the knowledge graph
 */
export interface Edge {
  src: string;
  dst: string;
  rel: EdgeRel;
  properties: Record<string, any>;
}

/**
 * Linear ticket interface
 */
export interface LinearTicket extends Node {
  type: NodeType.ISSUE;
  number: number;
  state: string;
  url: string;
}

/**
 * ADR interface
 */
export interface ADR extends Node {
  type: NodeType.ADR;
  status: string;
  path: string;
  decision_makers: string[];
}

/**
 * PR interface
 */
export interface PR extends Node {
  type: NodeType.PR;
  number: number;
  state: string;
  url: string;
  merged_at?: string;
  merged_by?: string;
}

/**
 * Commit interface
 */
export interface Commit extends Node {
  type: NodeType.COMMIT;
  author: string;
  sha: string;
  files: string[];
}

/**
 * File interface
 */
export interface File extends Node {
  type: NodeType.FILE;
  path: string;
  language?: string;
  last_modified?: string;
}

/**
 * GraphService class for interacting with the Arc Memory knowledge graph
 */
export class GraphService {
  private db: Database | null = null;
  private dbPath: string;
  private cache: NodeCache;
  private logger: Logger;
  private static DEFAULT_DB_PATH = path.join(os.homedir(), '.arc', 'graph.db');

  /**
   * Create a new GraphService instance
   * @param logger Logger instance
   * @param dbPath Optional path to the database file
   * @param cacheTTL Cache TTL in seconds (default: 300 seconds)
   */
  constructor(logger: Logger, dbPath?: string, cacheTTL: number = 300) {
    this.dbPath = dbPath || GraphService.DEFAULT_DB_PATH;
    this.logger = logger;
    this.cache = new NodeCache({ stdTTL: cacheTTL, checkperiod: 60 });
  }

  /**
   * Connect to the database
   * @returns A promise that resolves when the connection is established
   * @throws Error if the connection fails
   */
  async connect(): Promise<void> {
    try {
      // Check if the database file exists
      if (!fs.existsSync(this.dbPath)) {
        throw new Error(`Database file not found: ${this.dbPath}`);
      }

      this.db = await open({
        filename: this.dbPath,
        driver: sqlite3.Database,
        mode: sqlite3.OPEN_READONLY, // Open in read-only mode for safety
      });

      this.logger.info(`Connected to database at ${this.dbPath}`);
    } catch (error) {
      this.logger.error(`Failed to connect to database: ${error}`);
      throw new Error(`Failed to connect to database: ${error}`);
    }
  }

  /**
   * Close the database connection
   * @returns A promise that resolves when the connection is closed
   */
  async close(): Promise<void> {
    if (this.db) {
      await this.db.close();
      this.db = null;
      this.logger.info('Database connection closed');
    }
  }

  /**
   * Check if the database connection is open
   * @returns True if the connection is open, false otherwise
   */
  isConnected(): boolean {
    return this.db !== null;
  }

  /**
   * Ensure the database connection is open
   * @throws Error if the connection is not open
   */
  private ensureConnected(): void {
    if (!this.isConnected()) {
      throw new Error('Database not connected');
    }
  }

  /**
   * Get a node by its ID
   * @param id The ID of the node to retrieve
   * @returns The node, or null if not found
   */
  async getNodeById(id: string): Promise<Node | null> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `node:${id}`;
    const cachedNode = this.cache.get<Node>(cacheKey);
    if (cachedNode) {
      this.logger.debug(`Cache hit for node ${id}`);
      return cachedNode;
    }

    try {
      const node = await this.db!.get(
        'SELECT id, type, title, body, extra FROM nodes WHERE id = ?',
        [id]
      );

      if (!node) {
        return null;
      }

      // Parse the extra JSON field
      if (node.extra) {
        try {
          node.extra = JSON.parse(node.extra);
        } catch (error) {
          this.logger.warn(`Failed to parse extra field for node ${id}: ${error}`);
          node.extra = {};
        }
      } else {
        node.extra = {};
      }

      // Cache the result
      this.cache.set(cacheKey, node);
      return node;
    } catch (error) {
      this.logger.error(`Failed to get node ${id}: ${error}`);
      throw new Error(`Failed to get node ${id}: ${error}`);
    }
  }

  /**
   * Get edges by source node ID
   * @param srcId The ID of the source node
   * @param relType Optional relationship type to filter by
   * @returns An array of edges
   */
  async getEdgesBySrc(srcId: string, relType?: EdgeRel): Promise<Edge[]> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `edges:src:${srcId}:${relType || 'all'}`;
    const cachedEdges = this.cache.get<Edge[]>(cacheKey);
    if (cachedEdges) {
      this.logger.debug(`Cache hit for edges by source ${srcId}`);
      return cachedEdges;
    }

    try {
      let query = 'SELECT src, dst, rel, properties FROM edges WHERE src = ?';
      const params: any[] = [srcId];

      if (relType) {
        query += ' AND rel = ?';
        params.push(relType);
      }

      const edges = await this.db!.all(query, params);

      // Parse the properties JSON field
      const result = edges.map((edge) => {
        if (edge.properties) {
          try {
            edge.properties = JSON.parse(edge.properties);
          } catch (error) {
            this.logger.warn(`Failed to parse properties for edge ${edge.src}->${edge.dst}: ${error}`);
            edge.properties = {};
          }
        } else {
          edge.properties = {};
        }

        return edge;
      });

      // Cache the result
      this.cache.set(cacheKey, result);
      return result;
    } catch (error) {
      this.logger.error(`Failed to get edges for source ${srcId}: ${error}`);
      throw new Error(`Failed to get edges for source ${srcId}: ${error}`);
    }
  }

  /**
   * Get edges by destination node ID
   * @param dstId The ID of the destination node
   * @param relType Optional relationship type to filter by
   * @returns An array of edges
   */
  async getEdgesByDst(dstId: string, relType?: EdgeRel): Promise<Edge[]> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `edges:dst:${dstId}:${relType || 'all'}`;
    const cachedEdges = this.cache.get<Edge[]>(cacheKey);
    if (cachedEdges) {
      this.logger.debug(`Cache hit for edges by destination ${dstId}`);
      return cachedEdges;
    }

    try {
      let query = 'SELECT src, dst, rel, properties FROM edges WHERE dst = ?';
      const params: any[] = [dstId];

      if (relType) {
        query += ' AND rel = ?';
        params.push(relType);
      }

      const edges = await this.db!.all(query, params);

      // Parse the properties JSON field
      const result = edges.map((edge) => {
        if (edge.properties) {
          try {
            edge.properties = JSON.parse(edge.properties);
          } catch (error) {
            this.logger.warn(`Failed to parse properties for edge ${edge.src}->${edge.dst}: ${error}`);
            edge.properties = {};
          }
        } else {
          edge.properties = {};
        }

        return edge;
      });

      // Cache the result
      this.cache.set(cacheKey, result);
      return result;
    } catch (error) {
      this.logger.error(`Failed to get edges for destination ${dstId}: ${error}`);
      throw new Error(`Failed to get edges for destination ${dstId}: ${error}`);
    }
  }

  /**
   * Find Linear tickets related to a PR/branch
   * @param prNumber The PR number
   * @param owner The repository owner
   * @param repo The repository name
   * @returns An array of Linear tickets
   */
  async findLinearTicketsForPR(prNumber: number, owner: string, repo: string): Promise<LinearTicket[]> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `linear:pr:${owner}/${repo}/${prNumber}`;
    const cachedTickets = this.cache.get<LinearTicket[]>(cacheKey);
    if (cachedTickets) {
      this.logger.debug(`Cache hit for Linear tickets related to PR #${prNumber}`);
      return cachedTickets;
    }

    try {
      // First, get the PR node
      const prId = `pr:${owner}/${repo}#${prNumber}`;
      const prNode = await this.getNodeById(prId);

      if (!prNode) {
        this.logger.warn(`PR #${prNumber} not found in knowledge graph`);
        return [];
      }

      // Find all MENTIONS edges from the PR to issues
      const mentionsEdges = await this.getEdgesBySrc(prId, EdgeRel.MENTIONS);

      // Filter for Linear tickets (issue nodes with Linear URLs)
      const linearTickets: LinearTicket[] = [];

      for (const edge of mentionsEdges) {
        const node = await this.getNodeById(edge.dst);

        if (node && node.type === NodeType.ISSUE && node.extra && node.extra.url && node.extra.url.includes('linear.app')) {
          linearTickets.push({
            ...node,
            type: NodeType.ISSUE,
            number: node.extra.number,
            state: node.extra.state || 'unknown',
            url: node.extra.url,
          });
        }
      }

      // Cache the result
      this.cache.set(cacheKey, linearTickets);
      return linearTickets;
    } catch (error) {
      this.logger.error(`Failed to find Linear tickets for PR #${prNumber}: ${error}`);
      throw new Error(`Failed to find Linear tickets for PR #${prNumber}: ${error}`);
    }
  }

  /**
   * Retrieve ADRs related to changed files
   * @param changedFiles Array of file paths that were changed
   * @returns An array of ADRs
   */
  async findADRsForChangedFiles(changedFiles: string[]): Promise<ADR[]> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `adrs:files:${changedFiles.sort().join(',')}`;
    const cachedADRs = this.cache.get<ADR[]>(cacheKey);
    if (cachedADRs) {
      this.logger.debug(`Cache hit for ADRs related to changed files`);
      return cachedADRs;
    }

    try {
      const adrs: ADR[] = [];
      const processedADRIds = new Set<string>();

      for (const filePath of changedFiles) {
        // Get the file node
        const fileId = `file:${filePath}`;
        const fileNode = await this.getNodeById(fileId);

        if (!fileNode) {
          this.logger.debug(`File ${filePath} not found in knowledge graph`);
          continue;
        }

        // Find all DECIDES edges to the file
        const decidesEdges = await this.getEdgesByDst(fileId, EdgeRel.DECIDES);

        for (const edge of decidesEdges) {
          const node = await this.getNodeById(edge.src);

          if (node && node.type === NodeType.ADR && !processedADRIds.has(node.id)) {
            processedADRIds.add(node.id);
            adrs.push({
              ...node,
              type: NodeType.ADR,
              status: node.extra?.status || 'unknown',
              path: node.extra?.path || '',
              decision_makers: node.extra?.decision_makers || [],
            });
          }
        }
      }

      // Cache the result
      this.cache.set(cacheKey, adrs);
      return adrs;
    } catch (error) {
      this.logger.error(`Failed to find ADRs for changed files: ${error}`);
      throw new Error(`Failed to find ADRs for changed files: ${error}`);
    }
  }

  /**
   * Extract commit history and context for a PR
   * @param prNumber The PR number
   * @param owner The repository owner
   * @param repo The repository name
   * @returns An array of commits
   */
  async getCommitHistoryForPR(prNumber: number, owner: string, repo: string): Promise<Commit[]> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `commits:pr:${owner}/${repo}/${prNumber}`;
    const cachedCommits = this.cache.get<Commit[]>(cacheKey);
    if (cachedCommits) {
      this.logger.debug(`Cache hit for commits in PR #${prNumber}`);
      return cachedCommits;
    }

    try {
      // First, get the PR node
      const prId = `pr:${owner}/${repo}#${prNumber}`;
      const prNode = await this.getNodeById(prId);

      if (!prNode) {
        this.logger.warn(`PR #${prNumber} not found in knowledge graph`);
        return [];
      }

      // Find all MERGES edges from the PR to commits
      const mergesEdges = await this.getEdgesBySrc(prId, EdgeRel.MERGES);

      // Get the commit nodes
      const commits: Commit[] = [];

      for (const edge of mergesEdges) {
        const node = await this.getNodeById(edge.dst);

        if (node && node.type === NodeType.COMMIT) {
          commits.push({
            ...node,
            type: NodeType.COMMIT,
            author: node.extra?.author || 'unknown',
            sha: node.extra?.sha || '',
            files: node.extra?.files || [],
          });
        }
      }

      // Sort commits by timestamp (newest first)
      commits.sort((a, b) => {
        const aTime = a.extra?.timestamp ? new Date(a.extra.timestamp).getTime() : 0;
        const bTime = b.extra?.timestamp ? new Date(b.extra.timestamp).getTime() : 0;
        return bTime - aTime;
      });

      // Cache the result
      this.cache.set(cacheKey, commits);
      return commits;
    } catch (error) {
      this.logger.error(`Failed to get commit history for PR #${prNumber}: ${error}`);
      throw new Error(`Failed to get commit history for PR #${prNumber}: ${error}`);
    }
  }

  /**
   * Find related PRs for a file
   * @param filePath The file path
   * @returns An array of PRs
   */
  async findRelatedPRsForFile(filePath: string): Promise<PR[]> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `prs:file:${filePath}`;
    const cachedPRs = this.cache.get<PR[]>(cacheKey);
    if (cachedPRs) {
      this.logger.debug(`Cache hit for PRs related to file ${filePath}`);
      return cachedPRs;
    }

    try {
      // Get the file node
      const fileId = `file:${filePath}`;
      const fileNode = await this.getNodeById(fileId);

      if (!fileNode) {
        this.logger.warn(`File ${filePath} not found in knowledge graph`);
        return [];
      }

      // Find all commits that modified this file
      const modifiesEdges = await this.getEdgesByDst(fileId, EdgeRel.MODIFIES);

      // Find PRs that merged these commits
      const prs: PR[] = [];
      const processedPRIds = new Set<string>();

      for (const edge of modifiesEdges) {
        const commitId = edge.src;
        const mergedByEdges = await this.getEdgesByDst(commitId, EdgeRel.MERGES);

        for (const mergeEdge of mergedByEdges) {
          const prNode = await this.getNodeById(mergeEdge.src);

          if (prNode && prNode.type === NodeType.PR && !processedPRIds.has(prNode.id)) {
            processedPRIds.add(prNode.id);
            prs.push({
              ...prNode,
              type: NodeType.PR,
              number: prNode.extra?.number,
              state: prNode.extra?.state || 'unknown',
              url: prNode.extra?.url || '',
              merged_at: prNode.extra?.merged_at,
              merged_by: prNode.extra?.merged_by,
            });
          }
        }
      }

      // Sort PRs by number (newest first)
      prs.sort((a, b) => b.number - a.number);

      // Cache the result
      this.cache.set(cacheKey, prs);
      return prs;
    } catch (error) {
      this.logger.error(`Failed to find related PRs for file ${filePath}: ${error}`);
      throw new Error(`Failed to find related PRs for file ${filePath}: ${error}`);
    }
  }

  /**
   * Search for nodes in the knowledge graph
   * @param query The search query (e.g., "type:adr", "issue:ABC-123")
   * @returns An array of matching nodes
   */
  async searchNodes(query: string): Promise<Node[]> {
    this.ensureConnected();

    // Check cache first
    const cacheKey = `search:${query}`;
    const cachedNodes = this.cache.get<Node[]>(cacheKey);
    if (cachedNodes) {
      this.logger.debug(`Cache hit for search query "${query}"`);
      return cachedNodes;
    }

    try {
      let sqlQuery = 'SELECT id, type, title, body, extra FROM nodes';
      const params: any[] = [];

      // Parse the query
      if (query.includes('type:')) {
        const typeMatch = query.match(/type:(\w+)/);
        if (typeMatch && typeMatch[1]) {
          sqlQuery += ' WHERE type = ?';
          params.push(typeMatch[1]);
        }
      } else if (query.startsWith('issue:')) {
        sqlQuery += ' WHERE id LIKE ?';
        params.push(`%${query.substring(6)}%`);
      } else if (query.includes(':')) {
        const [field, value] = query.split(':');
        if (field && value) {
          sqlQuery += ' WHERE id LIKE ? OR title LIKE ?';
          params.push(`%${value}%`, `%${value}%`);
        }
      } else {
        // Full-text search if available, otherwise fallback to LIKE
        try {
          const ftsQuery = `SELECT id FROM fts_nodes WHERE body MATCH ?`;
          const ftsResults = await this.db!.all(ftsQuery, [query]);

          if (ftsResults.length > 0) {
            const ids = ftsResults.map(row => `'${row.id}'`).join(',');
            sqlQuery += ` WHERE id IN (${ids})`;
          } else {
            sqlQuery += ' WHERE title LIKE ? OR body LIKE ?';
            params.push(`%${query}%`, `%${query}%`);
          }
        } catch (ftsError) {
          // FTS may not be available, fall back to LIKE
          this.logger.warn(`FTS search failed, falling back to LIKE: ${ftsError}`);
          sqlQuery += ' WHERE title LIKE ? OR body LIKE ?';
          params.push(`%${query}%`, `%${query}%`);
        }
      }

      const nodes = await this.db!.all(sqlQuery, params);

      // Parse the extra JSON field
      const result = nodes.map((node) => {
        if (node.extra) {
          try {
            node.extra = JSON.parse(node.extra);
          } catch (error) {
            this.logger.warn(`Failed to parse extra field for node ${node.id}: ${error}`);
            node.extra = {};
          }
        } else {
          node.extra = {};
        }

        return node;
      });

      // Cache the result
      this.cache.set(cacheKey, result);
      return result;
    } catch (error) {
      this.logger.error(`Failed to search nodes with query "${query}": ${error}`);
      throw new Error(`Failed to search nodes with query "${query}": ${error}`);
    }
  }

  /**
   * Clear the cache
   */
  clearCache(): void {
    this.cache.flushAll();
    this.logger.info('Cache cleared');
  }

  /**
   * Get the database statistics
   * @returns An object with node and edge counts
   */
  async getStats(): Promise<{ nodeCount: number; edgeCount: number }> {
    this.ensureConnected();

    try {
      const nodeCountResult = await this.db!.get('SELECT COUNT(*) as count FROM nodes');
      const edgeCountResult = await this.db!.get('SELECT COUNT(*) as count FROM edges');

      return {
        nodeCount: nodeCountResult.count,
        edgeCount: edgeCountResult.count,
      };
    } catch (error) {
      this.logger.error(`Failed to get database statistics: ${error}`);
      throw new Error(`Failed to get database statistics: ${error}`);
    }
  }
}
