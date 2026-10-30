function val = getappdata(h, key)
val = appdata_store('get', key, []);
end
