import { Context } from 'probot';
import { GraphService, LinearTicket, ADR, Commit, PR, EdgeRel, NodeType } from './graph-service';

/**
 * Interface for a file change in a pull request.
 */
export interface FileChange {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch?: string;
}

/**
 * Interface for PR context information.
 */
export interface PRContext {
  prNumber: number;
  prTitle: string;
  prBody: string;
  prAuthor: string;
  baseRef: string;
  headRef: string;
  repository: string;
  owner: string;
  changedFiles: FileChange[];
  relatedEntities: {
    linearTickets: LinearTicket[];
    adrs: ADR[];
    commits: Commit[];
    relatedPRs: PR[];
  };
}

/**
 * Class to generate context for pull requests.
 * This class extracts information from the PR and queries the knowledge graph
 * to find related entities like Linear tickets and ADRs.
 */
export class ContextGenerator {
  private graphService: GraphService;

  /**
   * Create a new ContextGenerator.
   * @param graphService The GraphService instance to use for querying the knowledge graph.
   */
  constructor(graphService: GraphService) {
    this.graphService = graphService;
  }

  /**
   * Extract context information for a pull request.
   * @param context The Probot context object.
   * @returns A promise that resolves to the PR context.
   */
  async generateContext(context: Context<'pull_request'>): Promise<PRContext> {
    const pr = context.payload.pull_request;
    const repo = context.payload.repository;

    // Get the list of files changed in the PR
    const filesResponse = await context.octokit.pulls.listFiles({
      owner: repo.owner.login,
      repo: repo.name,
      pull_number: pr.number,
    });

    const changedFiles = filesResponse.data.map(file => ({
      filename: file.filename,
      status: file.status,
      additions: file.additions,
      deletions: file.deletions,
      changes: file.changes,
      patch: file.patch,
    }));

    // Extract related entities from the knowledge graph
    const [linearTickets, adrs, commits] = await Promise.all([
      this.findLinearTickets(pr.number, repo.owner.login, repo.name, pr.head.ref, pr.body || ''),
      this.findRelevantADRs(changedFiles.map(file => file.filename)),
      this.graphService.getCommitHistoryForPR(pr.number, repo.owner.login, repo.name),
    ]);

    // Find related PRs for the changed files
    const relatedPRPromises = changedFiles.map(file =>
      this.graphService.findRelatedPRsForFile(file.filename)
    );
    const relatedPRsArrays = await Promise.all(relatedPRPromises);

    // Flatten and deduplicate the related PRs
    const relatedPRsMap = new Map<string, PR>();
    relatedPRsArrays.flat().forEach(pr => {
      if (!relatedPRsMap.has(pr.id)) {
        relatedPRsMap.set(pr.id, pr);
      }
    });
    const relatedPRs = Array.from(relatedPRsMap.values());

    // Filter out the current PR from related PRs
    const filteredRelatedPRs = relatedPRs.filter(
      relatedPR => relatedPR.number !== pr.number
    );

    // Create the PR context object
    const prContext: PRContext = {
      prNumber: pr.number,
      prTitle: pr.title,
      prBody: pr.body || '',
      prAuthor: pr.user.login,
      baseRef: pr.base.ref,
      headRef: pr.head.ref,
      repository: repo.name,
      owner: repo.owner.login,
      changedFiles,
      relatedEntities: {
        linearTickets,
        adrs,
        commits,
        relatedPRs: filteredRelatedPRs,
      },
    };

    return prContext;
  }

  /**
   * Find Linear tickets related to a PR.
   * This method looks for tickets mentioned in the PR body and branch name,
   * and also queries the knowledge graph for tickets linked to the PR.
   * @param prNumber The PR number.
   * @param owner The repository owner.
   * @param repo The repository name.
   * @param branchName The branch name.
   * @param prBody The PR body.
   * @returns An array of Linear tickets.
   */
  private async findLinearTickets(
    prNumber: number,
    owner: string,
    repo: string,
    branchName: string,
    prBody: string
  ): Promise<LinearTicket[]> {
    // First, get tickets from the knowledge graph
    const graphTickets = await this.graphService.findLinearTicketsForPR(prNumber, owner, repo);
    
    // Create a map to deduplicate tickets
    const ticketsMap = new Map<string, LinearTicket>();
    graphTickets.forEach(ticket => {
      ticketsMap.set(ticket.id, ticket);
    });

    // Extract ticket IDs from branch name
    // Common formats: feature/ABC-123, bugfix/ABC-123, ABC-123-description
    const branchTicketMatches = branchName.match(/[A-Z]+-\d+/g);
    if (branchTicketMatches) {
      for (const ticketId of branchTicketMatches) {
        // If we don't already have this ticket, try to find it in the knowledge graph
        if (!ticketsMap.has(`issue:${ticketId}`)) {
          const ticket = await this.fetchLatestTicket(ticketId);
          if (ticket) {
            ticketsMap.set(ticket.id, ticket);
          }
        }
      }
    }

    // Extract ticket IDs from PR body
    // Look for formats like "Fixes ABC-123" or "Related to ABC-123"
    const bodyTicketMatches = prBody.match(/[A-Z]+-\d+/g);
    if (bodyTicketMatches) {
      for (const ticketId of bodyTicketMatches) {
        // If we don't already have this ticket, try to find it in the knowledge graph
        if (!ticketsMap.has(`issue:${ticketId}`)) {
          const ticket = await this.fetchLatestTicket(ticketId);
          if (ticket) {
            ticketsMap.set(ticket.id, ticket);
          }
        }
      }
    }

    return Array.from(ticketsMap.values());
  }

  /**
   * Fetch the latest information for a Linear ticket.
   * @param ticketId The ticket ID (e.g., "ABC-123").
   * @returns The ticket, or null if not found.
   */
  private async fetchLatestTicket(ticketId: string): Promise<LinearTicket | null> {
    try {
      // Try to find the ticket in the knowledge graph
      const nodes = await this.graphService.searchNodes(`issue:${ticketId}`);
      
      for (const node of nodes) {
        if (node.type === NodeType.ISSUE && node.id.includes(ticketId)) {
          return {
            ...node,
            type: NodeType.ISSUE,
            number: node.extra?.number || 0,
            state: node.extra?.state || 'unknown',
            url: node.extra?.url || '',
          };
        }
      }
      
      return null;
    } catch (error) {
      // If we can't find the ticket, return a placeholder
      return null;
    }
  }

  /**
   * Find relevant ADRs for the changed files.
   * This method queries the knowledge graph for ADRs that have DECIDES edges
   * to the changed files, and also looks for the most recent ADRs.
   * @param changedFiles Array of file paths that were changed.
   * @returns An array of ADRs.
   */
  private async findRelevantADRs(changedFiles: string[]): Promise<ADR[]> {
    // First, get ADRs directly related to the changed files
    const fileADRs = await this.graphService.findADRsForChangedFiles(changedFiles);
    
    // Create a map to deduplicate ADRs
    const adrsMap = new Map<string, ADR>();
    fileADRs.forEach(adr => {
      adrsMap.set(adr.id, adr);
    });

    // If we didn't find any ADRs directly related to the files,
    // try to find the most recent ADRs that might be relevant
    if (adrsMap.size === 0) {
      const latestADR = await this.fetchLatestADR();
      if (latestADR) {
        adrsMap.set(latestADR.id, latestADR);
      }
    }

    return Array.from(adrsMap.values());
  }

  /**
   * Fetch the latest ADR from the knowledge graph.
   * @returns The latest ADR, or null if none found.
   */
  private async fetchLatestADR(): Promise<ADR | null> {
    try {
      // Search for ADR nodes
      const nodes = await this.graphService.searchNodes('type:adr');
      
      if (nodes.length === 0) {
        return null;
      }
      
      // Sort by timestamp (newest first)
      nodes.sort((a, b) => {
        const aTime = a.extra?.timestamp ? new Date(a.extra.timestamp).getTime() : 0;
        const bTime = b.extra?.timestamp ? new Date(b.extra.timestamp).getTime() : 0;
        return bTime - aTime;
      });
      
      // Return the newest ADR
      const latestADR = nodes[0];
      return {
        ...latestADR,
        type: NodeType.ADR,
        status: latestADR.extra?.status || 'unknown',
        path: latestADR.extra?.path || '',
        decision_makers: latestADR.extra?.decision_makers || [],
      };
    } catch (error) {
      return null;
    }
  }
}
