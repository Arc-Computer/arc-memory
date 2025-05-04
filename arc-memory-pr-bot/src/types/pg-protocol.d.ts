declare module 'pg-protocol/dist/messages' {
  export interface NoticeMessage {
    message: string;
    severity: string;
    code: string;
    detail: string;
    hint: string;
    position: string;
    internalPosition: string;
    internalQuery: string;
    where: string;
    schema: string;
    table: string;
    column: string;
    dataType: string;
    constraint: string;
    file: string;
    line: string;
    routine: string;
  }
}
