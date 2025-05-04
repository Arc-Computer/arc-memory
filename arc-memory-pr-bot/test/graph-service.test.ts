import { describe, beforeEach, afterEach, test, expect, vi } from "vitest";
import { MockGraphService } from "../src/mock-graph-service";
import { NodeType, EdgeRel } from "../src/graph-service";

describe("GraphService", () => {
  let graphService: MockGraphService;
  const mockLogger = {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  };

  beforeEach(async () => {
    graphService = new MockGraphService(mockLogger as any);
    await graphService.connect();
  });

  afterEach(async () => {
    await graphService.close();
  });

  test("should connect and disconnect from the database", async () => {
    expect(graphService.isConnected()).toBe(true);
    await graphService.close();
    expect(graphService.isConnected()).toBe(false);
  });

  test("should get a node by ID", async () => {
    const node = await graphService.getNodeById("pr:Arc-Computer/arc-memory#1");
    expect(node).not.toBeNull();
    expect(node?.type).toBe(NodeType.PR);
    expect(node?.title).toBe("Add Linear OAuth integration");
  });

  test("should return null for non-existent node", async () => {
    const node = await graphService.getNodeById("non-existent-id");
    expect(node).toBeNull();
  });

  test("should get edges by source", async () => {
    const edges = await graphService.getEdgesBySrc("pr:Arc-Computer/arc-memory#1");
    expect(edges.length).toBeGreaterThan(0);
    expect(edges.some(edge => edge.rel === EdgeRel.MENTIONS)).toBe(true);
  });

  test("should get edges by destination", async () => {
    const edges = await graphService.getEdgesByDst("file:arc_memory/auth/linear.py");
    expect(edges.length).toBeGreaterThan(0);
    expect(edges.some(edge => edge.rel === EdgeRel.MODIFIES)).toBe(true);
  });

  test("should find Linear tickets related to a PR", async () => {
    const tickets = await graphService.findLinearTicketsForPR(1, "Arc-Computer", "arc-memory");
    expect(tickets.length).toBe(1);
    expect(tickets[0].title).toBe("Implement Linear OAuth flow");
    expect(tickets[0].number).toBe(42);
  });

  test("should return empty array for PR with no related Linear tickets", async () => {
    // PR #999 doesn't exist in our mock data
    const tickets = await graphService.findLinearTicketsForPR(999, "Arc-Computer", "arc-memory");
    expect(tickets.length).toBe(0);
  });

  test("should find ADRs related to changed files", async () => {
    const adrs = await graphService.findADRsForChangedFiles(["arc_memory/auth/linear.py"]);
    expect(adrs.length).toBe(2);
    expect(adrs.some(adr => adr.title === "Use SQLite for Knowledge Graph Storage")).toBe(true);
    expect(adrs.some(adr => adr.title === "Authentication Mechanisms")).toBe(true);
  });

  test("should return empty array for files with no related ADRs", async () => {
    const adrs = await graphService.findADRsForChangedFiles(["non-existent-file.py"]);
    expect(adrs.length).toBe(0);
  });

  test("should get commit history for a PR", async () => {
    const commits = await graphService.getCommitHistoryForPR(1, "Arc-Computer", "arc-memory");
    expect(commits.length).toBe(1);
    expect(commits[0].title).toBe("Add Linear OAuth implementation");
    expect(commits[0].sha).toBe("abc123");
  });

  test("should return empty array for PR with no commits", async () => {
    // PR #999 doesn't exist in our mock data
    const commits = await graphService.getCommitHistoryForPR(999, "Arc-Computer", "arc-memory");
    expect(commits.length).toBe(0);
  });

  test("should find related PRs for a file", async () => {
    const prs = await graphService.findRelatedPRsForFile("arc_memory/auth/linear.py");
    expect(prs.length).toBe(1);
    expect(prs[0].title).toBe("Add Linear OAuth integration");
    expect(prs[0].number).toBe(1);
  });

  test("should return empty array for file with no related PRs", async () => {
    const prs = await graphService.findRelatedPRsForFile("non-existent-file.py");
    expect(prs.length).toBe(0);
  });

  test("should get database statistics", async () => {
    const stats = await graphService.getStats();
    expect(stats.nodeCount).toBeGreaterThan(0);
    expect(stats.edgeCount).toBeGreaterThan(0);
  });

  test("should throw error when not connected", async () => {
    await graphService.close();
    await expect(graphService.getNodeById("pr:Arc-Computer/arc-memory#1")).rejects.toThrow("Database not connected");
  });

  describe("Caching behavior", () => {
    beforeEach(async () => {
      // Clear the cache before each test
      graphService.clearCache();
    });

    test("should cache higher-level query results for Linear tickets", async () => {
      // Spy on the lower-level methods
      const getNodeByIdSpy = vi.spyOn(graphService, "getNodeById");
      const getEdgesBySrcSpy = vi.spyOn(graphService, "getEdgesBySrc");

      // First call should use the lower-level methods
      const tickets1 = await graphService.findLinearTicketsForPR(1, "Arc-Computer", "arc-memory");
      expect(tickets1.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).toHaveBeenCalled();
      expect(getEdgesBySrcSpy).toHaveBeenCalled();

      // Reset the spies
      getNodeByIdSpy.mockClear();
      getEdgesBySrcSpy.mockClear();

      // Second call should use the cache
      const tickets2 = await graphService.findLinearTicketsForPR(1, "Arc-Computer", "arc-memory");
      expect(tickets2.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).not.toHaveBeenCalled();
      expect(getEdgesBySrcSpy).not.toHaveBeenCalled();

      // Verify the tickets are the same
      expect(tickets2).toEqual(tickets1);
    });

    test("should cache higher-level query results for ADRs", async () => {
      // Spy on the lower-level methods
      const getNodeByIdSpy = vi.spyOn(graphService, "getNodeById");
      const getEdgesByDstSpy = vi.spyOn(graphService, "getEdgesByDst");

      // First call should use the lower-level methods
      const adrs1 = await graphService.findADRsForChangedFiles(["arc_memory/auth/linear.py"]);
      expect(adrs1.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).toHaveBeenCalled();
      expect(getEdgesByDstSpy).toHaveBeenCalled();

      // Reset the spies
      getNodeByIdSpy.mockClear();
      getEdgesByDstSpy.mockClear();

      // Second call should use the cache
      const adrs2 = await graphService.findADRsForChangedFiles(["arc_memory/auth/linear.py"]);
      expect(adrs2.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).not.toHaveBeenCalled();
      expect(getEdgesByDstSpy).not.toHaveBeenCalled();

      // Verify the ADRs are the same
      expect(adrs2).toEqual(adrs1);
    });

    test("should cache higher-level query results for commits", async () => {
      // Spy on the lower-level methods
      const getNodeByIdSpy = vi.spyOn(graphService, "getNodeById");
      const getEdgesBySrcSpy = vi.spyOn(graphService, "getEdgesBySrc");

      // First call should use the lower-level methods
      const commits1 = await graphService.getCommitHistoryForPR(1, "Arc-Computer", "arc-memory");
      expect(commits1.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).toHaveBeenCalled();
      expect(getEdgesBySrcSpy).toHaveBeenCalled();

      // Reset the spies
      getNodeByIdSpy.mockClear();
      getEdgesBySrcSpy.mockClear();

      // Second call should use the cache
      const commits2 = await graphService.getCommitHistoryForPR(1, "Arc-Computer", "arc-memory");
      expect(commits2.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).not.toHaveBeenCalled();
      expect(getEdgesBySrcSpy).not.toHaveBeenCalled();

      // Verify the commits are the same
      expect(commits2).toEqual(commits1);
    });

    test("should cache higher-level query results for related PRs", async () => {
      // Spy on the lower-level methods
      const getNodeByIdSpy = vi.spyOn(graphService, "getNodeById");
      const getEdgesByDstSpy = vi.spyOn(graphService, "getEdgesByDst");

      // First call should use the lower-level methods
      const prs1 = await graphService.findRelatedPRsForFile("arc_memory/auth/linear.py");
      expect(prs1.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).toHaveBeenCalled();
      expect(getEdgesByDstSpy).toHaveBeenCalled();

      // Reset the spies
      getNodeByIdSpy.mockClear();
      getEdgesByDstSpy.mockClear();

      // Second call should use the cache
      const prs2 = await graphService.findRelatedPRsForFile("arc_memory/auth/linear.py");
      expect(prs2.length).toBeGreaterThan(0);
      expect(getNodeByIdSpy).not.toHaveBeenCalled();
      expect(getEdgesByDstSpy).not.toHaveBeenCalled();

      // Verify the PRs are the same
      expect(prs2).toEqual(prs1);
    });

    test("should invalidate cache when cleared", async () => {
      // First call to cache the result
      const tickets1 = await graphService.findLinearTicketsForPR(1, "Arc-Computer", "arc-memory");
      expect(tickets1.length).toBeGreaterThan(0);

      // Spy on the lower-level methods after the first call
      const getNodeByIdSpy = vi.spyOn(graphService, "getNodeById");
      const getEdgesBySrcSpy = vi.spyOn(graphService, "getEdgesBySrc");

      // Second call should use the cache
      await graphService.findLinearTicketsForPR(1, "Arc-Computer", "arc-memory");
      expect(getNodeByIdSpy).not.toHaveBeenCalled();
      expect(getEdgesBySrcSpy).not.toHaveBeenCalled();

      // Clear the cache
      graphService.clearCache();

      // Third call should hit the methods again
      await graphService.findLinearTicketsForPR(1, "Arc-Computer", "arc-memory");
      expect(getNodeByIdSpy).toHaveBeenCalled();
      expect(getEdgesBySrcSpy).toHaveBeenCalled();
    });
  });
});
