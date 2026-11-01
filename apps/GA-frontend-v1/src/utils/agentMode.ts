const AGENT_RENDERING_TYPES = new Set(['assistant', 'orchestrator', 'deepagent']);

export function getAgentType(agentConfig: any): string | null {
  return agentConfig?.basic?.type || agentConfig?.config?.basic?.type || null;
}

export function isAgentRenderingType(agentType: string | null | undefined): boolean {
  return !!agentType && AGENT_RENDERING_TYPES.has(agentType);
}

export function resolveAgentType(
  selectedAgentId: string | null | undefined,
  allAgents: any[] | undefined,
  activeAgentConfig: any
): string | null {
  const currentAgent = selectedAgentId
    ? (allAgents || []).find((agent: any) => agent.id === selectedAgentId)
    : null;

  return currentAgent?.config?.basic?.type || getAgentType(activeAgentConfig);
}

export function shouldUseAgentConversationFlow(params: {
  selectedAgentId?: string | null;
  allAgents?: any[];
  activeAgentConfig?: any;
}): boolean {
  const { selectedAgentId, allAgents, activeAgentConfig } = params;
  if (!(selectedAgentId || activeAgentConfig)) {
    return false;
  }

  return isAgentRenderingType(resolveAgentType(selectedAgentId, allAgents, activeAgentConfig));
}
