function out = appdata_store(op, key, val)
% Store behind the setappdata/getappdata shims (RunMat 0.6.1 has neither).
% A persistent struct, because a persistent containers.Map fails on RunMat
% with RunMat:SliceNonTensor when indexed.
persistent store
if isempty(store)
    store = struct();
end
out = [];
if strcmp(op, 'set')
    store.(key) = val;
elseif isfield(store, key)
    out = store.(key);
end
end
